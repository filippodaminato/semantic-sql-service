"""Router for Physical Ontology domain"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import List
from uuid import UUID
import re

from ..core.database import get_db
from ..db.models import (
    TableNode, ColumnNode, SchemaEdge, Datasource,
    RelationshipType, SQLEngineType
)
from ..schemas.ontology import (
    TableCreateDTO, TableResponseDTO, TableUpdateDTO, TableFullResponseDTO,
    ColumnUpdateDTO, ColumnResponseDTO,
    RelationshipCreateDTO, RelationshipResponseDTO, RelationshipUpdateDTO
)
from ..schemas.datasource import (
    DatasourceCreateDTO, DatasourceResponseDTO, DatasourceUpdateDTO
)
from ..services.embedding_service import embedding_service
from ..services.sql_validator import sql_validator
from ..core.logging import get_logger

logger = get_logger("ontology")

def slugify(text: str) -> str:
    return re.sub(r'[^a-z0-9]+', '-', text.lower()).strip('-')

router = APIRouter(prefix="/api/v1/ontology", tags=["Physical Ontology"])


@router.get("/datasources", response_model=List[DatasourceResponseDTO])
def get_datasources(db: Session = Depends(get_db)):
    """Get all datasources"""
    datasources = db.query(Datasource).all()
    return [DatasourceResponseDTO.model_validate(ds) for ds in datasources]


@router.post("/datasources", response_model=DatasourceResponseDTO, status_code=status.HTTP_201_CREATED)
def create_datasource(
    datasource_data: DatasourceCreateDTO,
    db: Session = Depends(get_db)
):
    """
    Create a datasource (helper endpoint).
    
    Required before creating tables as tables need a datasource_id.
    """
    # Auto-generate slug if not provided
    slug = datasource_data.slug
    if not slug:
        slug = datasource_data.name.lower().replace(" ", "-")

    # Check if name or slug already exists
    existing = db.query(Datasource).filter(
        (Datasource.name == datasource_data.name) | (Datasource.slug == slug)
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Datasource with name '{datasource_data.name}' or slug '{slug}' already exists"
        )
    
    # Generate embedding
    embedding = None
    if datasource_data.description or datasource_data.context_signature:
        embedding_text = f"{datasource_data.description or ''} {datasource_data.context_signature or ''}".strip()
        if embedding_text:
            embedding = embedding_service.generate_embedding(embedding_text)
    
    datasource = Datasource(
        name=datasource_data.name,
        slug=slug,
        description=datasource_data.description,
        engine=SQLEngineType(datasource_data.engine),
        context_signature=datasource_data.context_signature,
        embedding=embedding
    )
    
    try:
        db.add(datasource)
        db.commit()
        db.refresh(datasource)
        logger.info(f"Created datasource: {datasource.name} (ID: {datasource.id}, Slug: {datasource.slug})")
        return DatasourceResponseDTO.model_validate(datasource)
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating datasource: {str(e)}"
        )


@router.get("/datasources/{datasource_id}", response_model=DatasourceResponseDTO)
def get_datasource(
    datasource_id: UUID,
    db: Session = Depends(get_db)
):
    """Get a specific datasource"""
    datasource = db.query(Datasource).filter(Datasource.id == datasource_id).first()
    if not datasource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Datasource {datasource_id} not found"
        )
    return DatasourceResponseDTO.model_validate(datasource)


@router.put("/datasources/{datasource_id}", response_model=DatasourceResponseDTO)
def update_datasource(
    datasource_id: UUID,
    datasource_data: DatasourceUpdateDTO,
    db: Session = Depends(get_db)
):
    """Update a datasource"""
    datasource = db.query(Datasource).filter(Datasource.id == datasource_id).first()
    if not datasource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Datasource {datasource_id} not found"
        )
    
    update_embedding = False
    
    if datasource_data.name is not None:
        if datasource_data.name != datasource.name:
            existing = db.query(Datasource).filter(Datasource.name == datasource_data.name).first()
            if existing:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Datasource '{datasource_data.name}' already exists")
        datasource.name = datasource_data.name

    if datasource_data.slug is not None:
        if datasource_data.slug != datasource.slug:
            existing = db.query(Datasource).filter(Datasource.slug == datasource_data.slug).first()
            if existing:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Datasource slug '{datasource_data.slug}' already exists")
        datasource.slug = datasource_data.slug

    if datasource_data.description is not None:
        datasource.description = datasource_data.description
        update_embedding = True

    if datasource_data.engine is not None:
        datasource.engine = SQLEngineType(datasource_data.engine)

    if datasource_data.context_signature is not None:
        datasource.context_signature = datasource_data.context_signature
        update_embedding = True
        
    if update_embedding:
        embedding_text = f"{datasource.description or ''} {datasource.context_signature or ''}".strip()
        if embedding_text:
            datasource.embedding = embedding_service.generate_embedding(embedding_text)
        else:
            datasource.embedding = None
    
    try:
        db.commit()
        db.refresh(datasource)
        logger.info(f"Updated datasource: {datasource.name} (ID: {datasource.id})")
        return DatasourceResponseDTO.model_validate(datasource)
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating datasource: {str(e)}"
        )


@router.delete("/datasources/{datasource_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_datasource(
    datasource_id: UUID,
    db: Session = Depends(get_db)
):
    """Delete a datasource and cascade to tables"""
    datasource = db.query(Datasource).filter(Datasource.id == datasource_id).first()
    if not datasource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Datasource {datasource_id} not found"
        )
    
    try:
        db.delete(datasource)
        db.commit()
        logger.info(f"Deleted datasource: {datasource.name} (ID: {datasource_id})")
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting datasource: {str(e)}"
        )


@router.get("/tables", response_model=List[TableResponseDTO])
def get_tables(db: Session = Depends(get_db)):
    """Get all tables"""
    tables = db.query(TableNode).all()
    result = []
    for table in tables:
        table_dict = TableResponseDTO.model_validate(table).model_dump()
        # Load columns
        columns = db.query(ColumnNode).filter(ColumnNode.table_id == table.id).all()
        table_dict["columns"] = [ColumnResponseDTO.model_validate(col).model_dump() for col in columns]
        result.append(table_dict)
    return result


@router.post("/tables", response_model=TableResponseDTO, status_code=status.HTTP_201_CREATED)
def create_table_deep(
    table_data: TableCreateDTO,
    db: Session = Depends(get_db)
):
    """
    Deep Create: Create a table and optionally all its columns in a single transaction.
    
    - Validates physical_name is unique per datasource
    - Creates table with columns
    - Generates embeddings for semantic_name + description
    """
    # Validate datasource exists
    datasource = db.query(Datasource).filter(Datasource.id == table_data.datasource_id).first()
    if not datasource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Datasource {table_data.datasource_id} not found"
        )
    
    # Validate physical_name is unique for this datasource
    existing = db.query(TableNode).filter(
        and_(
            TableNode.datasource_id == table_data.datasource_id,
            TableNode.physical_name == table_data.physical_name
        )
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Table with physical_name '{table_data.physical_name}' already exists for this datasource"
        )
    
    try:
        # Generate embedding for table (semantic_name + description)
        embedding_text = f"{table_data.semantic_name}"
        if table_data.description:
            embedding_text += f" {table_data.description}"
        table_embedding = embedding_service.generate_embedding(embedding_text)
        
        # Create table
        table = TableNode(
            datasource_id=table_data.datasource_id,
            physical_name=table_data.physical_name,
            semantic_name=table_data.semantic_name,
            description=table_data.description,
            ddl_context=table_data.ddl_context,
            slug=table_data.slug or slugify(f"{datasource.slug}-{table_data.physical_name}"),
            embedding=table_embedding
        )
        db.add(table)
        db.flush()  # Get table.id
        
        # Create columns if provided
        columns = []
        for col_data in table_data.columns or []:
            # Generate embedding for column
            col_embedding_text = f"{col_data.name}"
            if col_data.semantic_name:
                col_embedding_text = f"{col_data.semantic_name}"
            if col_data.description:
                col_embedding_text += f" {col_data.description}"
            if col_data.context_note:
                col_embedding_text += f" {col_data.context_note}"
            
            col_embedding = embedding_service.generate_embedding(col_embedding_text)
            
            column = ColumnNode(
                table_id=table.id,
                name=col_data.name,
                semantic_name=col_data.semantic_name,
                data_type=col_data.data_type,
                is_primary_key=col_data.is_primary_key,
                description=col_data.description,
                context_note=col_data.context_note,
                slug=col_data.slug or slugify(f"{table.slug}-{col_data.name}"),
                embedding=col_embedding
            )
            db.add(column)
            columns.append(column)
        
        db.commit()
        db.refresh(table)
        
        # Return with columns
        response = TableResponseDTO.model_validate(table)
        response.columns = [ColumnResponseDTO.model_validate(col) for col in columns]
        logger.info(f"Created table (deep): {table.physical_name} (ID: {table.id}) with {len(columns)} columns")
        return response
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating table: {str(e)}"
        )


@router.get("/tables/{table_id}", response_model=TableResponseDTO)
def get_table(
    table_id: UUID,
    db: Session = Depends(get_db)
):
    """Get a specific table with columns"""
    table = db.query(TableNode).filter(TableNode.id == table_id).first()
    if not table:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Table {table_id} not found"
        )
    
    response = TableResponseDTO.model_validate(table)
    # Ensure columns are loaded
    columns = db.query(ColumnNode).filter(ColumnNode.table_id == table.id).all()
    response.columns = [ColumnResponseDTO.model_validate(col) for col in columns]
    return response


@router.get("/tables/{table_id}/full", response_model=TableFullResponseDTO)
def get_table_full(
    table_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Get a table with columns and ALL relationships (both incoming and outgoing).
    
    Returns:
    - Table details
    - All columns
    - Outgoing relationships (where this table's columns are source)
    - Incoming relationships (where this table's columns are target)
    """
    table = db.query(TableNode).filter(TableNode.id == table_id).first()
    if not table:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Table {table_id} not found"
        )
    
    # Get columns
    columns = db.query(ColumnNode).filter(ColumnNode.table_id == table.id).all()
    column_ids = [col.id for col in columns]
    
    # Get outgoing relationships (source is this table's columns)
    outgoing_edges = db.query(SchemaEdge).filter(
        SchemaEdge.source_column_id.in_(column_ids)
    ).all() if column_ids else []
    
    # Get incoming relationships (target is this table's columns)
    incoming_edges = db.query(SchemaEdge).filter(
        SchemaEdge.target_column_id.in_(column_ids)
    ).all() if column_ids else []
    
    def edge_to_dto(edge: SchemaEdge) -> dict:
        source_col = db.query(ColumnNode).filter(ColumnNode.id == edge.source_column_id).first()
        target_col = db.query(ColumnNode).filter(ColumnNode.id == edge.target_column_id).first()
        source_table = db.query(TableNode).filter(TableNode.id == source_col.table_id).first() if source_col else None
        target_table = db.query(TableNode).filter(TableNode.id == target_col.table_id).first() if target_col else None
        
        return {
            "id": edge.id,
            "source_column_id": edge.source_column_id,
            "source_column_name": source_col.name if source_col else "",
            "source_table_id": source_table.id if source_table else None,
            "source_table_name": source_table.physical_name if source_table else "",
            "target_column_id": edge.target_column_id,
            "target_column_name": target_col.name if target_col else "",
            "target_table_id": target_table.id if target_table else None,
            "target_table_name": target_table.physical_name if target_table else "",
            "relationship_type": edge.relationship_type.value if hasattr(edge.relationship_type, 'value') else str(edge.relationship_type),
            "is_inferred": edge.is_inferred,
            "description": edge.description,
            "created_at": edge.created_at
        }
    
    return {
        "id": table.id,
        "datasource_id": table.datasource_id,
        "physical_name": table.physical_name,
        "semantic_name": table.semantic_name,
        "description": table.description,
        "ddl_context": table.ddl_context,
        "created_at": table.created_at,
        "updated_at": table.updated_at,
        "columns": [ColumnResponseDTO.model_validate(col) for col in columns],
        "outgoing_relationships": [edge_to_dto(e) for e in outgoing_edges],
        "incoming_relationships": [edge_to_dto(e) for e in incoming_edges]
    }


@router.put("/tables/{table_id}", response_model=TableResponseDTO)
def update_table(
    table_id: UUID,
    table_data: TableUpdateDTO,
    db: Session = Depends(get_db)
):
    """Update table details"""
    table = db.query(TableNode).filter(TableNode.id == table_id).first()
    if not table:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Table {table_id} not found"
        )
    
    update_embedding = False
    if table_data.semantic_name is not None:
        table.semantic_name = table_data.semantic_name
        update_embedding = True
    if table_data.description is not None:
        table.description = table_data.description
        update_embedding = True
    if table_data.ddl_context is not None:
        table.ddl_context = table_data.ddl_context
        
    if update_embedding:
        embedding_text = f"{table.semantic_name}"
        if table.description:
            embedding_text += f" {table.description}"
        table.embedding = embedding_service.generate_embedding(embedding_text)
    
    try:
        db.commit()
        db.refresh(table)
        
        response = TableResponseDTO.model_validate(table)
        columns = db.query(ColumnNode).filter(ColumnNode.table_id == table.id).all()
        response.columns = [ColumnResponseDTO.model_validate(col) for col in columns]
        logger.info(f"Updated table: {table.physical_name} (ID: {table.id})")
        return response
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating table: {str(e)}"
        )


@router.delete("/tables/{table_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_table(
    table_id: UUID,
    db: Session = Depends(get_db)
):
    """Delete a table and cascade"""
    table = db.query(TableNode).filter(TableNode.id == table_id).first()
    if not table:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Table {table_id} not found"
        )
    
    try:
        db.delete(table)
        db.commit()
        logger.info(f"Deleted table: {table.physical_name} (ID: {table_id})")
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting table: {str(e)}"
        )


@router.patch("/columns/{column_id}", response_model=ColumnResponseDTO)
def update_column(
    column_id: UUID,
    column_data: ColumnUpdateDTO,
    db: Session = Depends(get_db)
):
    """
    Update a specific column (fine-grained update).
    
    - Updates only provided fields (partial update)
    - Triggers embedding recalculation if semantic fields changed
    """
    column = db.query(ColumnNode).filter(ColumnNode.id == column_id).first()
    if not column:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Column {column_id} not found"
        )
    
    # Update fields if provided
    update_embedding = False
    if column_data.semantic_name is not None:
        column.semantic_name = column_data.semantic_name
        update_embedding = True
    if column_data.description is not None:
        column.description = column_data.description
        update_embedding = True
    if column_data.context_note is not None:
        column.context_note = column_data.context_note
        update_embedding = True
    if column_data.is_primary_key is not None:
        column.is_primary_key = column_data.is_primary_key
    if column_data.data_type is not None:
        column.data_type = column_data.data_type
    
    # Recalculate embedding if semantic fields changed
    if update_embedding:
        embedding_text = column.semantic_name or column.name
        if column.description:
            embedding_text += f" {column.description}"
        if column.context_note:
            embedding_text += f" {column.context_note}"
        column.embedding = embedding_service.generate_embedding(embedding_text)
    
    try:
        db.commit()
        db.refresh(column)
        logger.info(f"Updated column: {column.name} (ID: {column.id})")
        return ColumnResponseDTO.model_validate(column)
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating column: {str(e)}"
        )


@router.get("/columns/{column_id}", response_model=ColumnResponseDTO)
def get_column(
    column_id: UUID,
    db: Session = Depends(get_db)
):
    """Get a specific column"""
    column = db.query(ColumnNode).filter(ColumnNode.id == column_id).first()
    if not column:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Column {column_id} not found"
        )
    return ColumnResponseDTO.model_validate(column)


@router.delete("/columns/{column_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_column(
    column_id: UUID,
    db: Session = Depends(get_db)
):
    """Delete a column"""
    column = db.query(ColumnNode).filter(ColumnNode.id == column_id).first()
    if not column:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Column {column_id} not found"
        )
    
    try:
        db.delete(column)
        db.commit()
        logger.info(f"Deleted column: {column.name} (ID: {column_id})")
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting column: {str(e)}"
        )


@router.post("/relationships", response_model=RelationshipResponseDTO, status_code=status.HTTP_201_CREATED)
def create_relationship(
    relationship_data: RelationshipCreateDTO,
    db: Session = Depends(get_db)
):
    """
    Define manual JOIN relationships.
    
    - Validates both columns exist
    - Validates source and target are different
    - Prevents duplicate relationships (idempotent)
    """
    # Validate source and target are different
    if relationship_data.source_column_id == relationship_data.target_column_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Source and target columns must be different"
        )
    
    # Validate columns exist
    source_col = db.query(ColumnNode).filter(ColumnNode.id == relationship_data.source_column_id).first()
    if not source_col:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Source column {relationship_data.source_column_id} not found"
        )
    
    target_col = db.query(ColumnNode).filter(ColumnNode.id == relationship_data.target_column_id).first()
    if not target_col:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Target column {relationship_data.target_column_id} not found"
        )
    
    # Check for duplicate relationship (idempotent)
    existing = db.query(SchemaEdge).filter(
        and_(
            SchemaEdge.source_column_id == relationship_data.source_column_id,
            SchemaEdge.target_column_id == relationship_data.target_column_id
        )
    ).first()
    
    if existing:
        # Idempotent: return existing relationship
        return RelationshipResponseDTO.model_validate(existing)
    
    # Create relationship
    relationship = SchemaEdge(
        source_column_id=relationship_data.source_column_id,
        target_column_id=relationship_data.target_column_id,
        relationship_type=RelationshipType(relationship_data.relationship_type),
        is_inferred=relationship_data.is_inferred,
        description=relationship_data.description
    )
    
    try:
        db.add(relationship)
        db.commit()
        db.refresh(relationship)
        logger.info(f"Created relationship: {relationship.relationship_type} (ID: {relationship.id})")
        return RelationshipResponseDTO.model_validate(relationship)
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating relationship: {str(e)}"
        )


@router.get("/relationships", response_model=List[RelationshipResponseDTO])
def get_relationships(
    db: Session = Depends(get_db)
):
    """Get all relationships"""
    relationships = db.query(SchemaEdge).all()
    return [RelationshipResponseDTO.model_validate(r) for r in relationships]


@router.get("/relationships/{relationship_id}", response_model=RelationshipResponseDTO)
def get_relationship(
    relationship_id: UUID,
    db: Session = Depends(get_db)
):
    """Get a specific relationship"""
    relationship = db.query(SchemaEdge).filter(SchemaEdge.id == relationship_id).first()
    if not relationship:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Relationship {relationship_id} not found"
        )
    return RelationshipResponseDTO.model_validate(relationship)


@router.put("/relationships/{relationship_id}", response_model=RelationshipResponseDTO)
def update_relationship(
    relationship_id: UUID,
    relationship_data: RelationshipUpdateDTO,
    db: Session = Depends(get_db)
):
    """Update a relationship"""
    relationship = db.query(SchemaEdge).filter(SchemaEdge.id == relationship_id).first()
    if not relationship:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Relationship {relationship_id} not found"
        )
    
    if relationship_data.relationship_type is not None:
        relationship.relationship_type = RelationshipType(relationship_data.relationship_type)
    if relationship_data.is_inferred is not None:
        relationship.is_inferred = relationship_data.is_inferred
    if relationship_data.description is not None:
        relationship.description = relationship_data.description
    
    try:
        db.commit()
        db.refresh(relationship)
        logger.info(f"Updated relationship: {relationship.id}")
        return RelationshipResponseDTO.model_validate(relationship)
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating relationship: {str(e)}"
        )


@router.delete("/relationships/{relationship_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_relationship(
    relationship_id: UUID,
    db: Session = Depends(get_db)
):
    """Delete a relationship"""
    relationship = db.query(SchemaEdge).filter(SchemaEdge.id == relationship_id).first()
    if not relationship:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Relationship {relationship_id} not found"
        )
    
    try:
        db.delete(relationship)
        db.commit()
        logger.info(f"Deleted relationship: {relationship_id}")
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting relationship: {str(e)}"
        )
