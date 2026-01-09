"""Router for Business Semantics domain"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID
import re

from ..core.database import get_db
from ..db.models import SemanticMetric, SemanticSynonym, SynonymTargetType, TableNode
from ..schemas.semantics import (
    MetricCreateDTO, MetricResponseDTO, MetricUpdateDTO,
    SynonymBulkDTO, SynonymResponseDTO, SynonymCreateDTO, SynonymUpdateDTO
)
from ..services.embedding_service import embedding_service
from ..services.sql_validator import sql_validator
from ..core.logging import get_logger

logger = get_logger("semantics")

def slugify(text: str) -> str:
    return re.sub(r'[^a-z0-9]+', '-', text.lower()).strip('-')

router = APIRouter(prefix="/api/v1/semantics", tags=["Business Semantics"])


@router.get("/metrics", response_model=List[MetricResponseDTO])
def get_metrics(db: Session = Depends(get_db)):
    """Get all metrics"""
    metrics = db.query(SemanticMetric).all()
    return [MetricResponseDTO.model_validate(m) for m in metrics]


@router.post("/metrics", response_model=MetricResponseDTO, status_code=status.HTTP_201_CREATED)
def create_metric(
    metric_data: MetricCreateDTO,
    db: Session = Depends(get_db)
):
    """
    Define a reusable business calculation (metric).
    
    - Validates SQL syntax with sqlglot (dry run)
    - Validates required tables exist
    - Generates embedding for retrieval
    """
    # Check if metric name already exists
    existing = db.query(SemanticMetric).filter(SemanticMetric.name == metric_data.name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Metric with name '{metric_data.name}' already exists"
        )
    
    # Validate required tables exist
    if metric_data.required_table_ids:
        tables = db.query(TableNode).filter(TableNode.id.in_(metric_data.required_table_ids)).all()
        found_ids = {str(t.id) for t in tables}
        required_ids = {str(tid) for tid in metric_data.required_table_ids}
        missing = required_ids - found_ids
        if missing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Required tables not found: {', '.join(missing)}"
            )
    
    # Validate SQL syntax (dry run)
    # Note: We use postgres as default dialect, but in production you'd get it from datasource
    is_valid, error_msg = sql_validator.validate_sql(metric_data.sql_expression, dialect="postgres")
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid SQL syntax: {error_msg}"
        )
    
    # Generate embedding
    embedding_text = f"{metric_data.name}"
    if metric_data.description:
        embedding_text += f" {metric_data.description}"
    embedding = embedding_service.generate_embedding(embedding_text)
    
    # Create metric
    metric = SemanticMetric(
        datasource_id=metric_data.datasource_id,
        name=metric_data.name,
        description=metric_data.description,
        calculation_sql=metric_data.sql_expression,
        required_tables=[str(tid) for tid in metric_data.required_table_ids] if metric_data.required_table_ids else None,
        filter_condition=metric_data.filter_condition,
        slug=metric_data.slug or slugify(metric_data.name),
        embedding=embedding
    )
    
    try:
        db.add(metric)
        db.commit()
        db.refresh(metric)
        logger.info(f"Created metric: {metric.name} (ID: {metric.id})")
        return MetricResponseDTO.model_validate(metric)
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating metric: {str(e)}"
        )


@router.get("/metrics/{metric_id}", response_model=MetricResponseDTO)
def get_metric(
    metric_id: UUID,
    db: Session = Depends(get_db)
):
    """Get a specific metric"""
    metric = db.query(SemanticMetric).filter(SemanticMetric.id == metric_id).first()
    if not metric:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Metric {metric_id} not found"
        )
    return MetricResponseDTO.model_validate(metric)


@router.put("/metrics/{metric_id}", response_model=MetricResponseDTO)
def update_metric(
    metric_id: UUID,
    metric_data: MetricUpdateDTO,
    db: Session = Depends(get_db)
):
    """Update a metric"""
    metric = db.query(SemanticMetric).filter(SemanticMetric.id == metric_id).first()
    if not metric:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Metric {metric_id} not found"
        )
    
    update_embedding = False
    if metric_data.name is not None:
        if metric_data.name != metric.name:
            existing = db.query(SemanticMetric).filter(SemanticMetric.name == metric_data.name).first()
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Metric '{metric_data.name}' already exists"
                )
        metric.name = metric_data.name
        update_embedding = True
    
    if metric_data.datasource_id is not None:
        metric.datasource_id = metric_data.datasource_id
    
    if metric_data.description is not None:
        metric.description = metric_data.description
        update_embedding = True
    
    if metric_data.sql_expression is not None:
        # Validate SQL
        is_valid, error_msg = sql_validator.validate_sql(metric_data.sql_expression, dialect="postgres")
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid SQL syntax: {error_msg}"
            )
        metric.calculation_sql = metric_data.sql_expression
    
    if metric_data.required_table_ids is not None:
        if metric_data.required_table_ids:
            tables = db.query(TableNode).filter(TableNode.id.in_(metric_data.required_table_ids)).all()
            found_ids = {str(t.id) for t in tables}
            required_ids = {str(tid) for tid in metric_data.required_table_ids}
            missing = required_ids - found_ids
            if missing:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Required tables not found: {', '.join(missing)}"
                )
        metric.required_tables = [str(tid) for tid in metric_data.required_table_ids]
    
    if metric_data.filter_condition is not None:
        metric.filter_condition = metric_data.filter_condition

    if update_embedding:
        embedding_text = f"{metric.name}"
        if metric.description:
            embedding_text += f" {metric.description}"
        metric.embedding = embedding_service.generate_embedding(embedding_text)
    
    try:
        db.commit()
        db.refresh(metric)
        logger.info(f"Updated metric: {metric.name} (ID: {metric.id})")
        return MetricResponseDTO.model_validate(metric)
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating metric: {str(e)}"
        )


@router.delete("/metrics/{metric_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_metric(
    metric_id: UUID,
    db: Session = Depends(get_db)
):
    """Delete a metric"""
    metric = db.query(SemanticMetric).filter(SemanticMetric.id == metric_id).first()
    if not metric:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Metric {metric_id} not found"
        )
    
    try:
        db.delete(metric)
        db.commit()
        logger.info(f"Deleted metric: {metric.name} (ID: {metric_id})")
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting metric: {str(e)}"
        )


@router.get("/synonyms", response_model=List[SynonymResponseDTO])
def get_synonyms(db: Session = Depends(get_db)):
    """Get all synonyms"""
    synonyms = db.query(SemanticSynonym).all()
    return [SynonymResponseDTO.model_validate(s) for s in synonyms]


@router.post("/synonyms/bulk", response_model=List[SynonymResponseDTO], status_code=status.HTTP_201_CREATED)
def create_synonyms_bulk(
    synonym_data: SynonymBulkDTO,
    db: Session = Depends(get_db)
):
    """
    Bulk insertion of synonyms for fast dictionary population.
    
    - Creates multiple synonym records in a single transaction
    - Handles duplicates idempotently (returns existing if found)
    """
    synonyms = []
    created_synonyms = []
    
    for term in synonym_data.terms:
        # Check if synonym already exists (idempotent)
        existing = db.query(SemanticSynonym).filter(
            SemanticSynonym.term == term,
            SemanticSynonym.target_type == SynonymTargetType(synonym_data.target_type),
            SemanticSynonym.target_id == synonym_data.target_id
        ).first()
        
        if existing:
            # Return existing (idempotent behavior)
            created_synonyms.append(SynonymResponseDTO.model_validate(existing))
            continue
        
        # Create new synonym
        synonym = SemanticSynonym(
            term=term,
            target_type=SynonymTargetType(synonym_data.target_type),
            target_id=synonym_data.target_id,
            slug=slugify(term)
        )
        synonyms.append(synonym)
        db.add(synonym)
    
    try:
        db.commit()
        # Refresh all created synonyms
        for synonym in synonyms:
            db.refresh(synonym)
            created_synonyms.append(SynonymResponseDTO.model_validate(synonym))
        
        logger.info(f"Created {len(synonyms)} synonyms (bulk)")
        return created_synonyms
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating synonyms: {str(e)}"
        )


@router.get("/synonyms/{synonym_id}", response_model=SynonymResponseDTO)
def get_synonym(
    synonym_id: UUID,
    db: Session = Depends(get_db)
):
    """Get a specific synonym"""
    synonym = db.query(SemanticSynonym).filter(SemanticSynonym.id == synonym_id).first()
    if not synonym:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Synonym {synonym_id} not found"
        )
    return SynonymResponseDTO.model_validate(synonym)


@router.post("/synonyms", response_model=SynonymResponseDTO, status_code=status.HTTP_201_CREATED)
def create_synonym(
    synonym_data: SynonymCreateDTO,
    db: Session = Depends(get_db)
):
    """Create a single synonym"""
    # Check if exists (idempotent)
    existing = db.query(SemanticSynonym).filter(
        SemanticSynonym.term == synonym_data.term,
        SemanticSynonym.target_type == SynonymTargetType(synonym_data.target_type),
        SemanticSynonym.target_id == synonym_data.target_id
    ).first()
    
    if existing:
        return SynonymResponseDTO.model_validate(existing)
    
    synonym = SemanticSynonym(
        term=synonym_data.term,
        target_type=SynonymTargetType(synonym_data.target_type),
        target_id=synonym_data.target_id,
        slug=synonym_data.slug or slugify(synonym_data.term)
    )
    
    try:
        db.add(synonym)
        db.commit()
        db.refresh(synonym)
        logger.info(f"Created synonym: {synonym.term} -> {synonym.target_id}")
        return SynonymResponseDTO.model_validate(synonym)
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating synonym: {str(e)}"
        )


@router.put("/synonyms/{synonym_id}", response_model=SynonymResponseDTO)
def update_synonym(
    synonym_id: UUID,
    synonym_data: SynonymUpdateDTO,
    db: Session = Depends(get_db)
):
    """Update a synonym"""
    synonym = db.query(SemanticSynonym).filter(SemanticSynonym.id == synonym_id).first()
    if not synonym:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Synonym {synonym_id} not found"
        )
    
    if synonym_data.term is not None:
        synonym.term = synonym_data.term
    if synonym_data.target_type is not None:
        synonym.target_type = SynonymTargetType(synonym_data.target_type)
    if synonym_data.target_id is not None:
        synonym.target_id = synonym_data.target_id
    
    try:
        db.commit()
        db.refresh(synonym)
        logger.info(f"Updated synonym: {synonym.id}")
        return SynonymResponseDTO.model_validate(synonym)
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating synonym: {str(e)}"
        )


@router.delete("/synonyms/{synonym_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_synonym(
    synonym_id: UUID,
    db: Session = Depends(get_db)
):
    """Delete a synonym"""
    synonym = db.query(SemanticSynonym).filter(SemanticSynonym.id == synonym_id).first()
    if not synonym:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Synonym {synonym_id} not found"
        )
    
    try:
        db.delete(synonym)
        db.commit()
        logger.info(f"Deleted synonym: {synonym.term} (ID: {synonym_id})")
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting synonym: {str(e)}"
        )
