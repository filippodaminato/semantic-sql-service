"""Router for Context & Values domain"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from ..core.database import get_db
from ..db.models import ColumnNode, LowCardinalityValue, ColumnContextRule
from ..schemas.context import (
    NominalValueCreateDTO, NominalValueResponseDTO, NominalValueUpdateDTO,
    ContextRuleDTO, ContextRuleResponseDTO, ContextRuleUpdateDTO
)
from ..services.embedding_service import embedding_service

router = APIRouter(prefix="/api/v1/context", tags=["Context & Values"])


@router.get("/nominal-values", response_model=List[NominalValueResponseDTO])
def get_nominal_values(db: Session = Depends(get_db)):
    """Get all nominal values"""
    values = db.query(LowCardinalityValue).all()
    return [NominalValueResponseDTO.model_validate(v) for v in values]


@router.post("/nominal-values", response_model=List[NominalValueResponseDTO], status_code=status.HTTP_201_CREATED)
def create_nominal_values(
    values_data: NominalValueCreateDTO,
    db: Session = Depends(get_db)
):
    """
    Map Real Value <-> Human Label for categorical columns.
    
    - Validates column exists
    - Creates multiple value mappings
    - Generates embeddings for labels
    - Handles duplicates idempotently
    """
    # Validate column exists
    column = db.query(ColumnNode).filter(ColumnNode.id == values_data.column_id).first()
    if not column:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Column {values_data.column_id} not found"
        )
    
    created_values = []
    new_values = []
    
    # Prepare labels for batch embedding
    labels = [item.label for item in values_data.values]
    embeddings = embedding_service.generate_embeddings_batch(labels)
    
    # Keep track of processed raw values in this batch to avoid duplicates
    processed_raw_values = set()
    
    for item, embedding in zip(values_data.values, embeddings):
        if item.raw in processed_raw_values:
            continue
        processed_raw_values.add(item.raw)

        # Check if value already exists (idempotent)
        existing = db.query(LowCardinalityValue).filter(
            LowCardinalityValue.column_id == values_data.column_id,
            LowCardinalityValue.value_raw == item.raw
        ).first()
        
        if existing:
            # Update existing with new label if different
            if existing.value_label != item.label:
                existing.value_label = item.label
                existing.embedding = embedding
                db.add(existing)
            created_values.append(existing)
            continue
        
        # Create new value
        value = LowCardinalityValue(
            column_id=values_data.column_id,
            value_raw=item.raw,
            value_label=item.label,
            embedding=embedding
        )
        new_values.append(value)
        db.add(value)
    
    try:
        db.commit()
        # Refresh all values
        all_values = new_values + created_values
        for value in all_values:
            db.refresh(value)
        
        # Return unique list (avoid duplicates)
        seen = set()
        unique_values = []
        for v in all_values:
            if v.id not in seen:
                seen.add(v.id)
                unique_values.append(NominalValueResponseDTO.model_validate(v))
        
        return unique_values
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating nominal values: {str(e)}"
        )


@router.get("/nominal-values/{value_id}", response_model=NominalValueResponseDTO)
def get_nominal_value(
    value_id: UUID,
    db: Session = Depends(get_db)
):
    """Get a specific nominal value"""
    value = db.query(LowCardinalityValue).filter(LowCardinalityValue.id == value_id).first()
    if not value:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Value {value_id} not found"
        )
    return NominalValueResponseDTO.model_validate(value)


@router.put("/nominal-values/{value_id}", response_model=NominalValueResponseDTO)
def update_nominal_value(
    value_id: UUID,
    value_data: NominalValueUpdateDTO,
    db: Session = Depends(get_db)
):
    """Update a nominal value"""
    value = db.query(LowCardinalityValue).filter(LowCardinalityValue.id == value_id).first()
    if not value:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Value {value_id} not found"
        )
    
    update_embedding = False
    if value_data.value_raw is not None:
        value.value_raw = value_data.value_raw
    
    if value_data.value_label is not None:
        value.value_label = value_data.value_label
        update_embedding = True
    
    if update_embedding:
        value.embedding = embedding_service.generate_embedding(value.value_label)
    
    try:
        db.commit()
        db.refresh(value)
        return NominalValueResponseDTO.model_validate(value)
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating nominal value: {str(e)}"
        )


@router.delete("/nominal-values/{value_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_nominal_value(
    value_id: UUID,
    db: Session = Depends(get_db)
):
    """Delete a nominal value"""
    value = db.query(LowCardinalityValue).filter(LowCardinalityValue.id == value_id).first()
    if not value:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Value {value_id} not found"
        )
    
    try:
        db.delete(value)
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting nominal value: {str(e)}"
        )


@router.get("/rules", response_model=List[ContextRuleResponseDTO])
def get_context_rules(db: Session = Depends(get_db)):
    """Get all context rules"""
    rules = db.query(ColumnContextRule).all()
    return [ContextRuleResponseDTO.model_validate(r) for r in rules]


@router.post("/rules", response_model=ContextRuleResponseDTO, status_code=status.HTTP_201_CREATED)
def create_context_rule(
    rule_data: ContextRuleDTO,
    db: Session = Depends(get_db)
):
    """
    Create a business rule for column interpretation.
    
    - Validates column exists
    - Generates embedding for rule text
    """
    # Validate column exists
    column = db.query(ColumnNode).filter(ColumnNode.id == rule_data.column_id).first()
    if not column:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Column {rule_data.column_id} not found"
        )
    
    # Generate embedding
    embedding = embedding_service.generate_embedding(rule_data.rule_text)
    
    # Create rule
    rule = ColumnContextRule(
        column_id=rule_data.column_id,
        rule_text=rule_data.rule_text,
        embedding=embedding
    )
    
    try:
        db.add(rule)
        db.commit()
        db.refresh(rule)
        return ContextRuleResponseDTO.model_validate(rule)
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating context rule: {str(e)}"
        )


@router.get("/rules/{rule_id}", response_model=ContextRuleResponseDTO)
def get_context_rule(
    rule_id: UUID,
    db: Session = Depends(get_db)
):
    """Get a specific context rule"""
    rule = db.query(ColumnContextRule).filter(ColumnContextRule.id == rule_id).first()
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rule {rule_id} not found"
        )
    return ContextRuleResponseDTO.model_validate(rule)


@router.put("/rules/{rule_id}", response_model=ContextRuleResponseDTO)
def update_context_rule(
    rule_id: UUID,
    rule_data: ContextRuleUpdateDTO,
    db: Session = Depends(get_db)
):
    """Update a context rule"""
    rule = db.query(ColumnContextRule).filter(ColumnContextRule.id == rule_id).first()
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rule {rule_id} not found"
        )
    
    if rule_data.rule_text is not None:
        rule.rule_text = rule_data.rule_text
        rule.embedding = embedding_service.generate_embedding(rule_data.rule_text)
    
    try:
        db.commit()
        db.refresh(rule)
        return ContextRuleResponseDTO.model_validate(rule)
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating context rule: {str(e)}"
        )


@router.delete("/rules/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_context_rule(
    rule_id: UUID,
    db: Session = Depends(get_db)
):
    """Delete a context rule"""
    rule = db.query(ColumnContextRule).filter(ColumnContextRule.id == rule_id).first()
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rule {rule_id} not found"
        )
    
    try:
        db.delete(rule)
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting context rule: {str(e)}"
        )
