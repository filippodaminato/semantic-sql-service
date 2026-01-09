"""
Router for Admin Control Plane endpoints.

This module consolidates all administration endpoints under /api/v1/admin/*
for the Control Plane interface (human administration panel).
"""
from fastapi import APIRouter, Depends, Query, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, Field
from datetime import datetime
import json
import re

def slugify(text: str) -> str:
    return re.sub(r'[^a-z0-9]+', '-', text.lower()).strip('-')

from ..core.database import get_db
from ..db.models import (
    Datasource, TableNode, ColumnNode, SchemaEdge,
    SemanticMetric, SemanticSynonym, ColumnContextRule,
    LowCardinalityValue, GoldenSQL,
    SQLEngineType, RelationshipType, SynonymTargetType
)
from ..services.sql_validator import sql_validator
from ..core.logging import get_logger

logger = get_logger("admin")


router = APIRouter(prefix="/api/v1/admin", tags=["Admin Control Plane"])


# =============================================================================
# SCHEMAS
# =============================================================================

class DatasourceCreate(BaseModel):
    name: str = Field(..., min_length=1)
    slug: Optional[str] = None
    engine: str = Field(default="postgres")
    description: Optional[str] = None
    context_signature: Optional[str] = None
    connection_string: Optional[str] = None


class DatasourceUpdate(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    description: Optional[str] = None
    context_signature: Optional[str] = None
    connection_string: Optional[str] = None


class DatasourceResponse(BaseModel):
    id: UUID
    name: str
    slug: str
    engine: str
    description: Optional[str]
    context_signature: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True


class TableCreate(BaseModel):
    datasource_id: UUID
    physical_name: str = Field(..., min_length=1)
    slug: Optional[str] = None
    semantic_name: str = Field(..., min_length=1)
    description: Optional[str] = None
    ddl_context: Optional[str] = None
    columns: Optional[List[dict]] = []


class TableUpdate(BaseModel):
    physical_name: Optional[str] = None
    slug: Optional[str] = None
    semantic_name: Optional[str] = None
    description: Optional[str] = None
    ddl_context: Optional[str] = None


class TableResponse(BaseModel):
    id: UUID
    datasource_id: UUID
    physical_name: str
    slug: str
    semantic_name: str
    description: Optional[str]
    ddl_context: Optional[str]
    created_at: datetime
    columns: List[dict] = []
    
    class Config:
        from_attributes = True


class ColumnUpdate(BaseModel):
    name: Optional[str] = None
    semantic_name: Optional[str] = None
    description: Optional[str] = None
    context_note: Optional[str] = None
    is_primary_key: Optional[bool] = None
    data_type: Optional[str] = None


class RelationshipCreate(BaseModel):
    source_column_id: UUID
    target_column_id: UUID
    relationship_type: str = Field(..., pattern="^(ONE_TO_ONE|ONE_TO_MANY|MANY_TO_MANY)$")
    is_inferred: bool = False
    description: Optional[str] = None

class RelationshipCreate(BaseModel):
    source_column_id: UUID
    target_column_id: UUID
    relationship_type: str = Field(..., pattern="^(ONE_TO_ONE|ONE_TO_MANY|MANY_TO_MANY)$")
    is_inferred: bool = False
    description: Optional[str] = None
    context_note: Optional[str] = None


class RelationshipUpdateDTO(BaseModel):
    relationship_type: Optional[str] = None
    is_inferred: Optional[bool] = None
    description: Optional[str] = None
    context_note: Optional[str] = None

class RelationshipResponseDTO(BaseModel):
    id: UUID
    source_column_id: UUID
    target_column_id: UUID
    relationship_type: str
    is_inferred: bool
    description: Optional[str]
    context_note: Optional[str]

    class Config:
        from_attributes = True

class MetricCreate(BaseModel):
    name: str = Field(..., min_length=1)
    slug: Optional[str] = None
    description: Optional[str] = None
    sql_expression: str = Field(..., min_length=1)
    required_table_ids: List[UUID] = []
    filter_condition: Optional[str] = None


class MetricUpdate(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    description: Optional[str] = None
    sql_expression: Optional[str] = None
    filter_condition: Optional[str] = None
    required_table_ids: Optional[List[UUID]] = None


class SynonymBulkCreate(BaseModel):
    target_id: UUID
    target_type: str = Field(..., pattern="^(TABLE|COLUMN|METRIC)$")
    terms: List[str] = Field(..., min_items=1)


class ContextRuleCreate(BaseModel):
    column_id: UUID
    slug: Optional[str] = None
    rule_text: str = Field(..., min_length=1)


class ValueManualCreate(BaseModel):
    raw: str
    slug: Optional[str] = None
    label: str


class ContextRuleUpdate(BaseModel):
    rule_text: str = Field(..., min_length=1)


class NominalValueUpdate(BaseModel):
    raw: Optional[str] = None
    label: Optional[str] = None



class GoldenSQLCreate(BaseModel):
    datasource_id: UUID
    slug: Optional[str] = None
    prompt_text: str = Field(..., min_length=1)
    sql_query: str = Field(..., min_length=1)
    complexity: int = Field(default=1, ge=1, le=5)
    verified: bool = False


class GoldenSQLImport(BaseModel):
    datasource_id: UUID
    items: List[dict]  # [{prompt_text, sql_query, complexity?}]


class RefreshIndexResponse(BaseModel):
    updated_count: int
    entities: List[str]


class ValidateMetricResponse(BaseModel):
    is_valid: bool
    error_message: Optional[str]
    sql_parsed: Optional[str]


# =============================================================================
# 1. DATASOURCES CRUD
# =============================================================================

@router.get("/datasources", response_model=List[DatasourceResponse])
def list_datasources(db: Session = Depends(get_db)):
    """List all configured datasources."""
    return db.query(Datasource).all()


@router.get("/datasources/{datasource_id}", response_model=DatasourceResponse)
def get_datasource(datasource_id: UUID, db: Session = Depends(get_db)):
    """Get a single datasource by ID."""
    ds = db.query(Datasource).filter(Datasource.id == datasource_id).first()
    if not ds:
        raise HTTPException(status_code=404, detail="Datasource not found")
    return ds


@router.post("/datasources", response_model=DatasourceResponse, status_code=201)
def create_datasource(data: DatasourceCreate, db: Session = Depends(get_db)):
    """Create a new datasource."""
    slug = data.slug or data.name.lower().replace(" ", "-")
    
    existing = db.query(Datasource).filter(
        (Datasource.name == data.name) | (Datasource.slug == slug)
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="Datasource name or slug already exists")
    
    ds = Datasource(
        name=data.name,
        slug=slug,
        engine=SQLEngineType(data.engine),
        description=data.description,
        context_signature=data.context_signature
    )
    db.add(ds)
    db.commit()
    db.refresh(ds)
    logger.info(f"Created datasource: {ds.name} (ID: {ds.id}, Slug: {ds.slug})")
    return ds


@router.put("/datasources/{datasource_id}", response_model=DatasourceResponse)
def update_datasource(datasource_id: UUID, data: DatasourceUpdate, db: Session = Depends(get_db)):
    """Update a datasource."""
    ds = db.query(Datasource).filter(Datasource.id == datasource_id).first()
    if not ds:
        raise HTTPException(status_code=404, detail="Datasource not found")
    
    if data.name is not None:
        ds.name = data.name
    if data.slug is not None:
        # Check uniqueness if slug changed
        if data.slug != ds.slug:
            existing = db.query(Datasource).filter(Datasource.slug == data.slug).first()
            if existing:
                raise HTTPException(status_code=409, detail=f"Slug '{data.slug}' already exists")
            ds.slug = data.slug
            
    if data.description is not None:
        ds.description = data.description
    if data.context_signature is not None:
        ds.context_signature = data.context_signature
            
    if data.connection_string is not None:
        ds.connection_string = data.connection_string
        
    db.commit()
    db.refresh(ds)
    logger.info(f"Updated datasource: {ds.name} (ID: {datasource_id})")
    return ds


@router.delete("/datasources/{datasource_id}", status_code=204)
def delete_datasource(datasource_id: UUID, db: Session = Depends(get_db)):
    """Delete a datasource and all related entities."""
    ds = db.query(Datasource).filter(Datasource.id == datasource_id).first()
    if not ds:
        raise HTTPException(status_code=404, detail="Datasource not found")
    db.delete(ds)
    db.commit()
    logger.info(f"Deleted datasource: {ds.name} (ID: {datasource_id})")


@router.post("/datasources/{datasource_id}/refresh-index", response_model=RefreshIndexResponse)
def refresh_datasource_index(datasource_id: UUID, db: Session = Depends(get_db)):
    """Force recalculation of all embeddings for a datasource."""
    ds = db.query(Datasource).filter(Datasource.id == datasource_id).first()
    if not ds:
        raise HTTPException(status_code=404, detail="Datasource not found")
    
    updated = []
    
    # Update datasource embedding
    # Update datasource embedding
    ds.update_embedding_if_needed()
    updated.append(f"datasource:{ds.name}")
    
    # Update table embeddings
    tables = db.query(TableNode).filter(TableNode.datasource_id == datasource_id).all()
    for table in tables:
        # Embedding update handled by Mixin
        table.update_embedding_if_needed()
        updated.append(f"table:{table.physical_name}")
        
        # Update column embeddings
        columns = db.query(ColumnNode).filter(ColumnNode.table_id == table.id).all()
        for col in columns:
            # Embedding update handled by Mixin
            col.update_embedding_if_needed()
            updated.append(f"column:{table.physical_name}.{col.name}")
    
    db.commit()
    return RefreshIndexResponse(updated_count=len(updated), entities=updated)


# =============================================================================
# 2. TABLES & COLUMNS CRUD
# =============================================================================

@router.get("/datasources/{datasource_id}/tables")
def list_tables_by_datasource(datasource_id: UUID, db: Session = Depends(get_db)):
    """Get all tables for a specific datasource."""
    ds = db.query(Datasource).filter(Datasource.id == datasource_id).first()
    if not ds:
        raise HTTPException(status_code=404, detail="Datasource not found")
    
    tables = db.query(TableNode).filter(TableNode.datasource_id == datasource_id).all()
    result = []
    for t in tables:
        cols = db.query(ColumnNode).filter(ColumnNode.table_id == t.id).all()
        result.append({
            "id": str(t.id),
            "physical_name": t.physical_name,
            "slug": t.slug,
            "semantic_name": t.semantic_name,
            "description": t.description,
            "column_count": len(cols),
            "columns": [
                {
                    "id": str(c.id), 
                    "name": c.name,
                    "slug": c.slug,
                    "semantic_name": c.semantic_name,
                    "data_type": c.data_type,
                    "is_primary_key": c.is_primary_key,
                    "description": c.description,
                    "context_note": c.context_note
                } for c in cols
            ],
            "created_at": t.created_at.isoformat() if t.created_at else None
        })
    return result


@router.post("/tables", status_code=201)
def create_table(data: TableCreate, db: Session = Depends(get_db)):
    """Create a table with optional columns."""
    ds = db.query(Datasource).filter(Datasource.id == data.datasource_id).first()
    if not ds:
        raise HTTPException(status_code=404, detail="Datasource not found")
    
    existing = db.query(TableNode).filter(
        and_(TableNode.datasource_id == data.datasource_id, TableNode.physical_name == data.physical_name)
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="Table already exists in this datasource")
    
    # Auto-generate slug if not provided
    table_slug = data.slug or slugify(f"{ds.slug}-{data.physical_name}")

    table = TableNode(
        datasource_id=data.datasource_id,
        physical_name=data.physical_name,
        slug=table_slug,
        semantic_name=data.semantic_name,
        description=data.description,
        ddl_context=data.ddl_context
    )
    db.add(table)
    db.flush()
    
    columns = []
    for col_data in data.columns or []:
        col_slug = col_data.get("slug") or slugify(f"{table_slug}-{col_data['name']}")
        col = ColumnNode(
            table_id=table.id,
            name=col_data["name"],
            slug=col_slug,
            semantic_name=col_data.get("semantic_name"),
            data_type=col_data["data_type"],
            is_primary_key=col_data.get("is_primary_key", False),
            description=col_data.get("description"),
            context_note=col_data.get("context_note")
        )
        db.add(col)
        columns.append(col)
    
    db.commit()
    db.refresh(table)
    
    logger.info(f"Created table: {table.physical_name} (ID: {table.id}, Slug: {table.slug}) in Datasource {table.datasource_id}")
    
    return {
        "id": str(table.id),
        "physical_name": table.physical_name,
        "slug": table.slug,
        "semantic_name": table.semantic_name,
        "columns": [{"id": str(c.id), "name": c.name, "slug": c.slug, "data_type": c.data_type} for c in columns]
    }


@router.get("/tables/{table_id}/full")
def get_table(table_id: UUID, db: Session = Depends(get_db)):
    """Get complete table details including columns, rules, and relationships."""
    table = db.query(TableNode).filter(TableNode.id == table_id).first()
    if not table:
        raise HTTPException(status_code=404, detail="Table not found")
    
    columns = db.query(ColumnNode).filter(ColumnNode.table_id == table.id).all()
    column_ids = [c.id for c in columns]
    col_map = {c.id: c.name for c in columns}
    
    # Get relationships
    outgoing = db.query(SchemaEdge).filter(SchemaEdge.source_column_id.in_(column_ids)).all() if column_ids else []
    incoming = db.query(SchemaEdge).filter(SchemaEdge.target_column_id.in_(column_ids)).all() if column_ids else []

    # Get Context Rules
    rules = db.query(ColumnContextRule).filter(ColumnContextRule.column_id.in_(column_ids)).all() if column_ids else []

    # Get Nominal Values
    values = db.query(LowCardinalityValue).filter(LowCardinalityValue.column_id.in_(column_ids)).all() if column_ids else []
    
    return {
        "id": str(table.id),
        "datasource_id": str(table.datasource_id),
        "physical_name": table.physical_name,
        "slug": table.slug,
        "semantic_name": table.semantic_name,
        "description": table.description,
        "ddl_context": table.ddl_context,
        "created_at": table.created_at.isoformat() if table.created_at else None,
        "context_rules": [
            {"id": str(r.id), "column_id": str(r.column_id), "slug": r.slug, "column_name": col_map.get(r.column_id), "rule_text": r.rule_text}
            for r in rules
        ],
        "nominal_values": [
            {"id": str(v.id), "column_id": str(v.column_id), "slug": v.slug, "column_name": col_map.get(v.column_id), "raw": v.value_raw, "label": v.value_label}
            for v in values
        ],
        "columns": [
            {
                "id": str(c.id),
                "name": c.name,
                "slug": c.slug,
                "semantic_name": c.semantic_name,
                "data_type": c.data_type,
                "is_primary_key": c.is_primary_key,
                "description": c.description,
                "context_note": c.context_note
            } for c in columns
        ],
        "relationship_count": len(outgoing) + len(incoming)
    }


@router.put("/tables/{table_id}")
def update_table(table_id: UUID, data: TableUpdate, db: Session = Depends(get_db)):
    """Update table properties."""
    table = db.query(TableNode).filter(TableNode.id == table_id).first()
    if not table:
        raise HTTPException(status_code=404, detail="Table not found")
    
    if data.physical_name is not None:
        table.physical_name = data.physical_name
    
    if data.slug is not None and data.slug != table.slug:
        # Check uniqueness
        existing = db.query(TableNode).filter(TableNode.slug == data.slug).first()
        if existing:
            raise HTTPException(status_code=409, detail=f"Slug '{data.slug}' already exists")
        table.slug = data.slug

    if data.semantic_name is not None:
        table.semantic_name = data.semantic_name
    if data.description is not None:
        table.description = data.description
    if data.ddl_context is not None:
        table.ddl_context = data.ddl_context
    
    db.commit()
    db.refresh(table)
    logger.info(f"Updated table: {table.physical_name} (ID: {table.id})")
    return {
        "id": str(table.id),
        "physical_name": table.physical_name,
        "slug": table.slug,
        "semantic_name": table.semantic_name,
        "description": table.description,
        "updated": True
    }


@router.delete("/tables/{table_id}", status_code=204)
def delete_table(table_id: UUID, db: Session = Depends(get_db)):
    """Delete a table and cascade."""
    table = db.query(TableNode).filter(TableNode.id == table_id).first()
    if not table:
        raise HTTPException(status_code=404, detail="Table not found")
    db.delete(table)
    db.commit()
    logger.info(f"Deleted table: {table.physical_name} (ID: {table_id})")


@router.put("/columns/{column_id}")
def update_column(column_id: UUID, data: ColumnUpdate, db: Session = Depends(get_db)):
    """Update column properties."""
    col = db.query(ColumnNode).filter(ColumnNode.id == column_id).first()
    if not col:
        raise HTTPException(status_code=404, detail="Column not found")
    
    if data.name is not None:
        # Check for duplicate name if changing
        if data.name != col.name:
            existing = db.query(ColumnNode).filter(
                ColumnNode.table_id == col.table_id,
                ColumnNode.name == data.name
            ).first()
            if existing:
                raise HTTPException(status_code=400, detail="Column with this name already exists")
            col.name = data.name

    if data.semantic_name is not None:
        col.semantic_name = data.semantic_name
    if data.description is not None:
        col.description = data.description
    if data.context_note is not None:
        col.context_note = data.context_note
    if data.is_primary_key is not None:
        col.is_primary_key = data.is_primary_key
    if data.data_type is not None:
        col.data_type = data.data_type
    
    db.commit()
    db.refresh(col)
    logger.info(f"Updated column: {col.name} (ID: {col.id})")
    return {"id": str(col.id), "name": col.name, "updated": True}


@router.delete("/columns/{column_id}", status_code=204)
def delete_column(column_id: UUID, db: Session = Depends(get_db)):
    """Delete a column."""
    col = db.query(ColumnNode).filter(ColumnNode.id == column_id).first()
    if not col:
         raise HTTPException(status_code=404, detail="Column not found")
    db.delete(col)
    db.commit()
    logger.info(f"Deleted column: {col.name} (ID: {column_id})")


@router.post("/tables/{table_id}/columns", status_code=201)
def create_column(table_id: UUID, data: dict, db: Session = Depends(get_db)):
    """Add a new column to a table."""
    table = db.query(TableNode).filter(TableNode.id == table_id).first()
    if not table:
        raise HTTPException(status_code=404, detail="Table not found")
        
    # Check if column exists
    existing = db.query(ColumnNode).filter(
        ColumnNode.table_id == table_id, 
        ColumnNode.name == data["name"]
    ).first()
    
    if existing:
         raise HTTPException(status_code=400, detail="Column with this name already exists")

    new_col = ColumnNode(
        table_id=table_id,
        name=data["name"],
        data_type=data.get("data_type", "VARCHAR"),
        is_primary_key=data.get("is_primary_key", False),
        semantic_name=data.get("semantic_name"),
        description=data.get("description"),
        context_note=data.get("context_note")
    )
    
    # Generate slug
    # We need table slug. Since we don't have it easily loaded on object yet (flush needed?), fetch it.
    # table is already fetched above.
    # Accessing table.slug might fail if not loaded? table is from query.
    new_col.slug = data.get("slug") or slugify(f"{table.slug}-{new_col.name}")

    
    db.add(new_col)
    db.commit()
    db.refresh(new_col)
    logger.info(f"Created column: {new_col.name} (ID: {new_col.id}) in Table {table.physical_name}")
    
    return {
        "id": str(new_col.id),
        "name": new_col.name,
        "data_type": new_col.data_type,
        "is_primary_key": new_col.is_primary_key,
        "id": str(new_col.id),
        "name": new_col.name,
        "slug": new_col.slug,
        "data_type": new_col.data_type,
        "is_primary_key": new_col.is_primary_key,
        "semantic_name": new_col.semantic_name,
        "description": new_col.description,
        "context_note": new_col.context_note
    }



# =============================================================================
# 3. RELATIONSHIPS CRUD
# =============================================================================

@router.get("/datasources/{datasource_id}/relationships")
def get_datasource_relationships(datasource_id: UUID, db: Session = Depends(get_db)):
    """Get all relationships between tables in a specific datasource."""
    ds = db.query(Datasource).filter(Datasource.id == datasource_id).first()
    if not ds:
        raise HTTPException(status_code=404, detail="Datasource not found")

    tables = db.query(TableNode).filter(TableNode.datasource_id == datasource_id).all()
    if not tables:
        return []

    table_ids = [t.id for t in tables]
    
    columns = db.query(ColumnNode).filter(ColumnNode.table_id.in_(table_ids)).all()
    column_ids = [c.id for c in columns]
    
    if not column_ids:
        return []

    relationships = db.query(SchemaEdge).filter(
        (SchemaEdge.source_column_id.in_(column_ids)) | 
        (SchemaEdge.target_column_id.in_(column_ids))
    ).all()

    def edge_to_dict(e):
        src_col = db.query(ColumnNode).filter(ColumnNode.id == e.source_column_id).first()
        tgt_col = db.query(ColumnNode).filter(ColumnNode.id == e.target_column_id).first()
        src_tbl = db.query(TableNode).filter(TableNode.id == src_col.table_id).first() if src_col else None
        tgt_tbl = db.query(TableNode).filter(TableNode.id == tgt_col.table_id).first() if tgt_col else None
        
        return {
            "id": str(e.id),
            "source_column_id": str(e.source_column_id),
            "target_column_id": str(e.target_column_id),
            "source_datasource_id": str(src_tbl.datasource_id) if src_tbl else None,
            "source_table": src_tbl.physical_name if src_tbl else None,
            "source_column": src_col.name if src_col else None,
            "target_datasource_id": str(tgt_tbl.datasource_id) if tgt_tbl else None,
            "target_table": tgt_tbl.physical_name if tgt_tbl else None,
            "target_column": tgt_col.name if tgt_col else None,
            "relationship_type": e.relationship_type.value if hasattr(e.relationship_type, 'value') else str(e.relationship_type),
            "description": e.description,
            "context_note": e.context_note,
            "is_inferred": e.is_inferred
        }

    return [edge_to_dict(r) for r in relationships]

@router.get("/tables/{table_id}/relationships")
def get_table_relationships(table_id: UUID, db: Session = Depends(get_db)):
    """Get all relationships (incoming and outgoing) for a table."""
    table = db.query(TableNode).filter(TableNode.id == table_id).first()
    if not table:
        raise HTTPException(status_code=404, detail="Table not found")
    
    columns = db.query(ColumnNode).filter(ColumnNode.table_id == table.id).all()
    column_ids = [c.id for c in columns]
    
    if not column_ids:
        return {"outgoing": [], "incoming": []}
    
    outgoing = db.query(SchemaEdge).filter(SchemaEdge.source_column_id.in_(column_ids)).all()
    incoming = db.query(SchemaEdge).filter(SchemaEdge.target_column_id.in_(column_ids)).all()
    
    def edge_to_dict(e, direction):
        src_col = db.query(ColumnNode).filter(ColumnNode.id == e.source_column_id).first()
        tgt_col = db.query(ColumnNode).filter(ColumnNode.id == e.target_column_id).first()
        src_tbl = db.query(TableNode).filter(TableNode.id == src_col.table_id).first() if src_col else None
        tgt_tbl = db.query(TableNode).filter(TableNode.id == tgt_col.table_id).first() if tgt_col else None
        return {
            "id": str(e.id),
            "direction": direction,
            "source_table": src_tbl.physical_name if src_tbl else None,
            "source_column": src_col.name if src_col else None,
            "target_table": tgt_tbl.physical_name if tgt_tbl else None,
            "target_column": tgt_col.name if tgt_col else None,
            "relationship_type": e.relationship_type.value if hasattr(e.relationship_type, 'value') else str(e.relationship_type),
            "description": e.description,
            "is_inferred": e.is_inferred
        }
    
    return {
        "outgoing": [edge_to_dict(e, "outgoing") for e in outgoing],
        "incoming": [edge_to_dict(e, "incoming") for e in incoming]
    }


@router.post("/relationships", status_code=201)
def create_relationship(data: RelationshipCreate, db: Session = Depends(get_db)):
    """Create a manual relationship between columns."""
    if data.source_column_id == data.target_column_id:
        raise HTTPException(status_code=400, detail="Source and target must be different")
    
    src = db.query(ColumnNode).filter(ColumnNode.id == data.source_column_id).first()
    tgt = db.query(ColumnNode).filter(ColumnNode.id == data.target_column_id).first()
    if not src:
        raise HTTPException(status_code=404, detail="Source column not found")
    if not tgt:
        raise HTTPException(status_code=404, detail="Target column not found")
    
    # Check for duplicate
    existing = db.query(SchemaEdge).filter(
        and_(SchemaEdge.source_column_id == data.source_column_id,
             SchemaEdge.target_column_id == data.target_column_id)
    ).first()
    if existing:
        return {"id": str(existing.id), "message": "Relationship already exists"}
    
    edge = SchemaEdge(
        source_column_id=data.source_column_id,
        target_column_id=data.target_column_id,
        relationship_type=RelationshipType(data.relationship_type),
        is_inferred=data.is_inferred,
        description=data.description,
        context_note=data.context_note
    )
    db.add(edge)
    db.commit()
    db.refresh(edge)
    logger.info(f"Created relationship: {edge.relationship_type} (ID: {edge.id})")
    return {"id": str(edge.id), "created": True}


@router.put("/relationships/{relationship_id}", response_model=RelationshipResponseDTO)
def update_relationship(
    relationship_id: UUID, 
    relationship_data: RelationshipUpdateDTO, 
    db: Session = Depends(get_db)
):
    """Update a relationship"""
    relationship = db.query(SchemaEdge).filter(SchemaEdge.id == relationship_id).first()
    if not relationship:
        raise HTTPException(status_code=404, detail=f"Relationship {relationship_id} not found")
    
    if relationship_data.relationship_type is not None:
        relationship.relationship_type = RelationshipType(relationship_data.relationship_type)
    if relationship_data.is_inferred is not None:
        relationship.is_inferred = relationship_data.is_inferred
    if relationship_data.description is not None:
        relationship.description = relationship_data.description
    if relationship_data.context_note is not None:
        relationship.context_note = relationship_data.context_note
    
    try:
        db.commit()
        db.refresh(relationship)
        return relationship
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error updating relationship: {str(e)}")


@router.delete("/relationships/{relationship_id}", status_code=204)
def delete_relationship(relationship_id: UUID, db: Session = Depends(get_db)):
    """Delete a relationship."""
    edge = db.query(SchemaEdge).filter(SchemaEdge.id == relationship_id).first()
    if not edge:
        raise HTTPException(status_code=404, detail="Relationship not found")
    db.delete(edge)
    db.commit()
    logger.info(f"Deleted relationship: {relationship_id}")


# =============================================================================
# 4. METRICS CRUD
# =============================================================================

@router.get("/metrics")
def list_metrics(datasource_id: Optional[UUID] = None, db: Session = Depends(get_db)):
    """List all metrics, optionally filtered by datasource."""
    query = db.query(SemanticMetric)
    metrics = query.all()
    
    if datasource_id:
        # Filter metrics relevant to this datasource (via required tables)
        ds_tables = db.query(TableNode.id).filter(TableNode.datasource_id == datasource_id).all()
        ds_table_ids = {str(t.id) for t in ds_tables}
        
        filtered = []
        for m in metrics:
            # If no tables required, maybe it's global? For now assume it's NOT specific to this DS unless listed.
            # Or if required_tables is empty, it might be invalid or global.
            if not m.required_tables:
                continue 
            if any(tid in ds_table_ids for tid in m.required_tables):
                filtered.append(m)
        metrics = filtered

    return [
        {
            "id": str(m.id),
            "name": m.name,
            "slug": m.slug,
            "description": m.description,
            "calculation_sql": m.calculation_sql,
            "filter_condition": m.filter_condition,
            "required_table_ids": m.required_tables,
            "created_at": m.created_at.isoformat() if m.created_at else None
        } for m in metrics
    ]

@router.delete("/metrics/{metric_id}", status_code=204)
def delete_metric(metric_id: UUID, db: Session = Depends(get_db)):
    """Delete a metric."""
    metric = db.query(SemanticMetric).filter(SemanticMetric.id == metric_id).first()
    if not metric:
        raise HTTPException(status_code=404, detail="Metric not found")
    db.delete(metric)
    db.commit()
    logger.info(f"Deleted metric: {metric.name} (ID: {metric_id})")


@router.post("/metrics", status_code=201)
def create_metric(data: MetricCreate, db: Session = Depends(get_db)):
    """Create a metric definition with SQL validation."""
    # Validate SQL
    is_valid, error = sql_validator.validate_sql(data.sql_expression)
    if not is_valid:
        raise HTTPException(status_code=400, detail=f"Invalid SQL: {error}")
    
    # Check name uniqueness
    existing = db.query(SemanticMetric).filter(SemanticMetric.name == data.name).first()
    if existing:
        raise HTTPException(status_code=409, detail="Metric name already exists")
    
    # Validate table IDs
    for tid in data.required_table_ids:
        t = db.query(TableNode).filter(TableNode.id == tid).first()
        if not t:
            raise HTTPException(status_code=404, detail=f"Table {tid} not found")
    
    metric_slug = data.slug or slugify(data.name)

    metric = SemanticMetric(
        name=data.name,
        slug=metric_slug,
        description=data.description,
        calculation_sql=data.sql_expression,
        filter_condition=data.filter_condition,
        required_tables=[str(tid) for tid in data.required_table_ids]  # Store as JSON list
    )
    db.add(metric)
    db.commit()
    db.refresh(metric)
    logger.info(f"Created metric: {metric.name} (ID: {metric.id}, Slug: {metric.slug})")
    return {"id": str(metric.id), "name": metric.name, "slug": metric.slug, "created": True}


@router.put("/metrics/{metric_id}")
def update_metric(metric_id: UUID, data: MetricUpdate, db: Session = Depends(get_db)):
    """Update a metric definition."""
    metric = db.query(SemanticMetric).filter(SemanticMetric.id == metric_id).first()
    if not metric:
        raise HTTPException(status_code=404, detail="Metric not found")
    
    if data.name is not None:
        metric.name = data.name
    
    if data.slug is not None and data.slug != metric.slug:
        # Check uniqueness
        existing = db.query(SemanticMetric).filter(SemanticMetric.slug == data.slug).first()
        if existing:
            raise HTTPException(status_code=409, detail=f"Slug '{data.slug}' already exists")
        metric.slug = data.slug

    if data.description is not None:
        metric.description = data.description
    if data.sql_expression is not None:
        is_valid, error = sql_validator.validate_sql(data.sql_expression)
        if not is_valid:
            raise HTTPException(status_code=400, detail=f"Invalid SQL: {error}")
        metric.calculation_sql = data.sql_expression
    if data.filter_condition is not None:
        metric.filter_condition = data.filter_condition
    
    if data.required_table_ids is not None:
        # Validate table IDs
        for tid in data.required_table_ids:
            t = db.query(TableNode).filter(TableNode.id == tid).first()
            if not t:
                raise HTTPException(status_code=404, detail=f"Table {tid} not found")
        metric.required_tables = [str(tid) for tid in data.required_table_ids]

    db.commit()
    logger.info(f"Updated metric: {metric.name} (ID: {metric.id})")
    return {"id": str(metric.id), "slug": metric.slug, "name": metric.name, "updated": True}


@router.post("/metrics/{metric_id}/validate", response_model=ValidateMetricResponse)
def validate_metric(metric_id: UUID, db: Session = Depends(get_db)):
    """Validate (dry-run) a metric's SQL expression."""
    metric = db.query(SemanticMetric).filter(SemanticMetric.id == metric_id).first()
    if not metric:
        raise HTTPException(status_code=404, detail="Metric not found")
    
    is_valid, error = sql_validator.validate_sql(metric.calculation_sql)
    return ValidateMetricResponse(
        is_valid=is_valid,
        error_message=error if not is_valid else None,
        sql_parsed=metric.calculation_sql if is_valid else None
    )


# =============================================================================
# 5. SYNONYMS CRUD
# =============================================================================

@router.get("/synonyms")
def list_synonyms(target_type: Optional[str] = None, db: Session = Depends(get_db)):
    """List all synonyms, optionally filtered by target type."""
    query = db.query(SemanticSynonym)
    if target_type:
        query = query.filter(SemanticSynonym.target_type == SynonymTargetType(target_type))
    return [
        {
            "id": str(s.id),
            "term": s.term,
            "slug": s.slug,
            "target_type": s.target_type.value if hasattr(s.target_type, 'value') else str(s.target_type),
            "target_id": str(s.target_id)
        } for s in query.all()
    ]


@router.post("/synonyms/bulk", status_code=201)
def create_synonyms_bulk(data: SynonymBulkCreate, db: Session = Depends(get_db)):
    """Bulk create synonyms for a target entity."""
    created = []
    for term in data.terms:
        existing = db.query(SemanticSynonym).filter(
            and_(SemanticSynonym.term == term, SemanticSynonym.target_id == data.target_id)
        ).first()
        if existing:
            created.append({"id": str(existing.id), "term": term, "existed": True})
            continue
        
        # Friendly slug: syn-{target_name}-{term}
        target_name = "unknown"
        if data.target_type == "TABLE":
            t = db.query(TableNode).filter(TableNode.id == data.target_id).first()
            if t: target_name = t.physical_name
        elif data.target_type == "COLUMN":
            c = db.query(ColumnNode).filter(ColumnNode.id == data.target_id).first()
            if c: target_name = c.name
        elif data.target_type == "METRIC":
            m = db.query(SemanticMetric).filter(SemanticMetric.id == data.target_id).first()
            if m: target_name = m.name
            
        syn_slug = slugify(f"{term}") # Try simple term first
        
        # Check collision, fallback to target_name prefixed
        if db.query(SemanticSynonym).filter(SemanticSynonym.slug == syn_slug).first():
             syn_slug = slugify(f"{term}-{target_name}")
             
        # Fallback to random hash if still collision
        if db.query(SemanticSynonym).filter(SemanticSynonym.slug == syn_slug).first():
             syn_slug = slugify(f"{term}-{str(hash(data.target_id))[-4:]}")

        syn = SemanticSynonym(
            term=term,
            slug=syn_slug,
            target_type=SynonymTargetType(data.target_type),
            target_id=data.target_id
        )
        db.add(syn)
        db.flush()
        created.append({"id": str(syn.id), "term": term, "slug": syn.slug, "existed": False})
    
    db.commit()
    logger.info(f"Bulk created {len(created)} synonyms for Target {data.target_id} ({data.target_type})")
    return created


@router.put("/synonyms/{synonym_id}")
def update_synonym(synonym_id: UUID, data: dict, db: Session = Depends(get_db)):
    """Update a synonym term."""
    syn = db.query(SemanticSynonym).filter(SemanticSynonym.id == synonym_id).first()
    if not syn:
        raise HTTPException(status_code=404, detail="Synonym not found")
    
    if "term" in data:
        syn.term = data["term"]
        # Update embedding
        # Assuming embedding_service is available in scope
        # syn.embedding = embedding_service.generate_embedding(syn.term) # Uncomment if embeddings are used on synonyms
    
    db.commit()
    return {"id": str(syn.id), "term": syn.term, "updated": True}


@router.delete("/synonyms/{synonym_id}", status_code=204)
def delete_synonym(synonym_id: UUID, db: Session = Depends(get_db)):
    """Delete a synonym."""
    syn = db.query(SemanticSynonym).filter(SemanticSynonym.id == synonym_id).first()
    if not syn:
        raise HTTPException(status_code=404, detail="Synonym not found")
    db.delete(syn)
    db.commit()
    logger.info(f"Deleted synonym: {syn.term} (ID: {synonym_id})")


# =============================================================================
# 6. CONTEXT RULES CRUD
# =============================================================================

@router.post("/context-rules", status_code=201)
def create_context_rule(data: ContextRuleCreate, db: Session = Depends(get_db)):
    """Associate a context rule with a column."""
    col = db.query(ColumnNode).filter(ColumnNode.id == data.column_id).first()
    if not col:
        raise HTTPException(status_code=404, detail="Column not found")
    
    # Generate slug
    # col is fetched above
    rule_hash = str(hash(data.rule_text))[-8:]
    rule_slug = data.slug or slugify(f"rule-{col.slug}-{rule_hash}")

    rule = ColumnContextRule(
        column_id=data.column_id,
        slug=rule_slug,
        rule_text=data.rule_text
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)
    logger.info(f"Created context rule for Column {data.column_id} (ID: {rule.id})")
    return {"id": str(rule.id), "rule_text": rule.rule_text, "slug": rule.slug, "created": True}


@router.get("/columns/{column_id}/rules")
def get_column_rules(column_id: UUID, db: Session = Depends(get_db)):
    """Get all context rules for a column."""
    col = db.query(ColumnNode).filter(ColumnNode.id == column_id).first()
    if not col:
        raise HTTPException(status_code=404, detail="Column not found")
    
    rules = db.query(ColumnContextRule).filter(ColumnContextRule.column_id == column_id).all()
    return [{"id": str(r.id), "rule_text": r.rule_text, "slug": r.slug, "created_at": r.created_at.isoformat() if r.created_at else None} for r in rules]


@router.delete("/context-rules/{rule_id}", status_code=204)
def delete_context_rule(rule_id: UUID, db: Session = Depends(get_db)):
    """Delete a context rule."""
    rule = db.query(ColumnContextRule).filter(ColumnContextRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    db.delete(rule)
    db.commit()
    logger.info(f"Deleted context rule: {rule_id}")


@router.put("/context-rules/{rule_id}")
def update_context_rule(rule_id: UUID, data: ContextRuleUpdate, db: Session = Depends(get_db)):
    """Update a context rule."""
    rule = db.query(ColumnContextRule).filter(ColumnContextRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    
    rule.rule_text = data.rule_text
    
    db.commit()
    logger.info(f"Updated context rule: {rule.id}")
    return {"id": str(rule.id), "rule_text": rule.rule_text, "updated": True}



# =============================================================================
# 7. NOMINAL VALUES CRUD
# =============================================================================

@router.get("/columns/{column_id}/values")
def get_column_values(column_id: UUID, db: Session = Depends(get_db)):
    """Get all nominal values mapped for a column."""
    col = db.query(ColumnNode).filter(ColumnNode.id == column_id).first()
    if not col:
        raise HTTPException(status_code=404, detail="Column not found")
    
    values = db.query(LowCardinalityValue).filter(LowCardinalityValue.column_id == column_id).all()
    return [{"id": str(v.id), "raw": v.value_raw, "label": v.value_label, "slug": v.slug} for v in values]


@router.post("/columns/{column_id}/values/sync")
def sync_column_values(column_id: UUID, db: Session = Depends(get_db)):
    """
    Trigger sync from real database (placeholder).
    In production, this would execute SELECT DISTINCT on the actual database.
    """
    col = db.query(ColumnNode).filter(ColumnNode.id == column_id).first()
    if not col:
        raise HTTPException(status_code=404, detail="Column not found")
    
    # Placeholder: In production, connect to datasource and query
    return {
        "message": "Sync triggered (placeholder - implement real DB connection)",
        "column_id": str(column_id),
        "synced_count": 0
    }


@router.post("/columns/{column_id}/values/manual", status_code=201)
def add_column_value_manual(column_id: UUID, data: ValueManualCreate, db: Session = Depends(get_db)):
    """Manually add or update a value mapping."""
    col = db.query(ColumnNode).filter(ColumnNode.id == column_id).first()
    if not col:
        raise HTTPException(status_code=404, detail="Column not found")
    
    existing = db.query(LowCardinalityValue).filter(
        and_(LowCardinalityValue.column_id == column_id, LowCardinalityValue.value_raw == data.raw)
    ).first()
    
    if existing:
        existing.value_label = data.label
        db.commit()
        return {"id": str(existing.id), "updated": True}
    
    # Generate slug
    val_slug = data.slug or slugify(f"val-{col.slug}-{data.raw}")
    
    value = LowCardinalityValue(
        column_id=column_id,
        slug=val_slug,
        value_raw=data.raw,
        value_label=data.label
    )
    db.add(value)
    db.commit()
    db.refresh(value)
    logger.info(f"Created manual value mapping for Column {column_id} (ID: {value.id})")
    return {"id": str(value.id), "slug": value.slug, "created": True}


@router.delete("/values/{value_id}", status_code=204)
def delete_column_value(value_id: UUID, db: Session = Depends(get_db)):
    """Delete a nominal value mapping."""
    val = db.query(LowCardinalityValue).filter(LowCardinalityValue.id == value_id).first()
    if not val:
        raise HTTPException(status_code=404, detail="Value mapping not found")
    db.delete(val)
    db.commit()


@router.put("/values/{value_id}")
def update_column_value(value_id: UUID, data: NominalValueUpdate, db: Session = Depends(get_db)):
    """Update a nominal value mapping."""
    val = db.query(LowCardinalityValue).filter(LowCardinalityValue.id == value_id).first()
    if not val:
        raise HTTPException(status_code=404, detail="Value mapping not found")
    
    if data.raw is not None:
        val.value_raw = data.raw
    if data.label is not None:
        val.value_label = data.label
        
    db.commit()
    logger.info(f"Updated manual value mapping: {val.id}")
    return {"id": str(val.id), "raw": val.value_raw, "label": val.value_label, "updated": True}



# =============================================================================
# 8. GOLDEN SQL CRUD
# =============================================================================

@router.get("/golden-sql")
def list_golden_sql(
    datasource_id: Optional[UUID] = None,
    complexity: Optional[int] = None,
    verified_only: bool = False,
    db: Session = Depends(get_db)
):
    """List golden SQL examples with filters."""
    query = db.query(GoldenSQL)
    if datasource_id:
        query = query.filter(GoldenSQL.datasource_id == datasource_id)
    if complexity:
        query = query.filter(GoldenSQL.complexity_score == complexity)
    if verified_only:
        query = query.filter(GoldenSQL.verified == True)
    
    return [
        {
            "id": str(g.id),
            "datasource_id": str(g.datasource_id),
            "prompt_text": g.prompt_text,
            "slug": g.slug,
            "sql_query": g.sql_query,
            "complexity_score": g.complexity_score,
            "verified": g.verified,
            "created_at": g.created_at.isoformat() if g.created_at else None
        } for g in query.all()
    ]


@router.post("/golden-sql", status_code=201)
def create_golden_sql(data: GoldenSQLCreate, db: Session = Depends(get_db)):
    """Add a new few-shot example."""
    ds = db.query(Datasource).filter(Datasource.id == data.datasource_id).first()
    if not ds:
        raise HTTPException(status_code=404, detail="Datasource not found")
    
    # Validate SQL
    dialect = ds.engine.value if hasattr(ds.engine, 'value') else str(ds.engine)
    is_valid, error = sql_validator.validate_sql(data.sql_query, dialect=dialect)
    if not is_valid:
        raise HTTPException(status_code=400, detail=f"Invalid SQL: {error}")
    
    # Generate slug
    gsql_slug = data.slug or slugify(f"gsql-{ds.slug}-{str(hash(data.prompt_text))[-8:]}")

    golden = GoldenSQL(
        datasource_id=data.datasource_id,
        slug=gsql_slug,
        prompt_text=data.prompt_text,
        sql_query=data.sql_query,
        complexity_score=data.complexity,
        verified=data.verified
    )
    db.add(golden)
    db.commit()
    db.refresh(golden)
    logger.info(f"Created Golden SQL example (ID: {golden.id})")
    return {"id": str(golden.id), "created": True}


@router.put("/golden-sql/{golden_sql_id}")
def update_golden_sql(golden_sql_id: UUID, data: dict, db: Session = Depends(get_db)):
    """Update a golden SQL example."""
    golden = db.query(GoldenSQL).filter(GoldenSQL.id == golden_sql_id).first()
    if not golden:
        raise HTTPException(status_code=404, detail="Golden SQL not found")
    
    if "prompt_text" in data:
        golden.prompt_text = data["prompt_text"]
    if "sql_query" in data:
        is_valid, error = sql_validator.validate_sql(data["sql_query"])
        if not is_valid:
            raise HTTPException(status_code=400, detail=f"Invalid SQL: {error}")
        golden.sql_query = data["sql_query"]
    if "complexity" in data:
        golden.complexity_score = data["complexity"]
    if "verified" in data:
        golden.verified = data["verified"]
    
    db.commit()
    logger.info(f"Updated Golden SQL example: {golden.id}")
    return {"id": str(golden.id), "updated": True}


@router.delete("/golden-sql/{golden_sql_id}", status_code=204)
def delete_golden_sql(golden_sql_id: UUID, db: Session = Depends(get_db)):
    """Delete a golden SQL example."""
    golden = db.query(GoldenSQL).filter(GoldenSQL.id == golden_sql_id).first()
    if not golden:
        raise HTTPException(status_code=404, detail="Golden SQL not found")
    db.delete(golden)
    db.commit()
    logger.info(f"Deleted Golden SQL: {golden_sql_id}")



@router.post("/golden-sql/import")
def import_golden_sql(data: GoldenSQLImport, db: Session = Depends(get_db)):
    """Bulk import golden SQL examples from CSV/JSON data."""
    ds = db.query(Datasource).filter(Datasource.id == data.datasource_id).first()
    if not ds:
        raise HTTPException(status_code=404, detail="Datasource not found")
    
    dialect = ds.engine.value if hasattr(ds.engine, 'value') else str(ds.engine)
    imported = []
    errors = []
    
    for idx, item in enumerate(data.items):
        prompt = item.get("prompt_text") or item.get("question")
        sql = item.get("sql_query") or item.get("sql")
        complexity = item.get("complexity", 1)
        
        if not prompt or not sql:
            errors.append({"index": idx, "error": "Missing prompt_text or sql_query"})
            continue
        
        is_valid, error = sql_validator.validate_sql(sql, dialect=dialect)
        if not is_valid:
            errors.append({"index": idx, "error": f"Invalid SQL: {error}"})
            continue
        
        # Auto-gen slug for import
        gsql_slug = slugify(f"gsql-{ds.slug}-{str(hash(prompt))[-8:]}")

        golden = GoldenSQL(
            datasource_id=data.datasource_id,
            slug=gsql_slug,
            prompt_text=prompt,
            sql_query=sql,
            complexity_score=complexity,
            verified=False
        )
        db.add(golden)
        imported.append({"prompt_text": prompt[:50] + "..."})
    
    db.commit()
    logger.info(f"Imported {len(imported)} Golden SQL items (Errors: {len(errors)})")
    return {
        "imported_count": len(imported),
        "error_count": len(errors),
        "errors": errors[:10]  # Limit error output
    }


# =============================================================================
# GRAPH VISUALIZATION (kept from original)
# =============================================================================

class GraphNode(BaseModel):
    id: str
    type: str
    data: dict
    position: dict


class GraphEdge(BaseModel):
    id: str
    source: str
    target: str
    sourceHandle: Optional[str] = None
    targetHandle: Optional[str] = None
    type: str
    animated: bool = False
    label: Optional[str] = None
    data: dict


class GraphVisualizationResponse(BaseModel):
    nodes: List[GraphNode]
    edges: List[GraphEdge]
    metadata: dict


@router.get("/graph/visualize", response_model=GraphVisualizationResponse)
def visualize_graph(
    datasource_id: Optional[UUID] = Query(None),
    include_columns: bool = Query(False),
    layout: str = Query("horizontal"),
    db: Session = Depends(get_db)
):
    """Generate graph payload for React Flow / D3.js visualization."""
    nodes = []
    edges = []
    
    tables_query = db.query(TableNode)
    if datasource_id:
        tables_query = tables_query.filter(TableNode.datasource_id == datasource_id)
    tables = tables_query.all()
    
    datasources = db.query(Datasource).all()
    ds_map = {ds.id: ds for ds in datasources}
    
    h_spacing = 350 if layout == "horizontal" else 300
    v_spacing = 200 if layout == "horizontal" else 250
    
    for idx, table in enumerate(tables):
        x = (idx % 4) * h_spacing + 50
        y = (idx // 4) * v_spacing + 50
        
        columns = db.query(ColumnNode).filter(ColumnNode.table_id == table.id).all()
        ds = ds_map.get(table.datasource_id)
        
        nodes.append({
            "id": f"table-{table.id}",
            "type": "table",
            "data": {
                "label": table.semantic_name or table.physical_name,
                "physical_name": table.physical_name,
                "semantic_name": table.semantic_name,
                "description": table.description,
                "datasource": ds.name if ds else "Unknown",
                "datasource_id": str(table.datasource_id),
                "column_count": len(columns),
                "columns": [c.name for c in columns],
                "primary_keys": [c.name for c in columns if c.is_primary_key]
            },
            "position": {"x": x, "y": y}
        })
        
        if include_columns:
            for ci, col in enumerate(columns):
                nodes.append({
                    "id": f"column-{col.id}",
                    "type": "column",
                    "data": {"label": col.name, "data_type": col.data_type, "is_pk": col.is_primary_key},
                    "position": {"x": x, "y": y + 100 + ci * 40},
                    "parentNode": f"table-{table.id}"
                })
    
    col_ids = [c.id for t in tables for c in db.query(ColumnNode).filter(ColumnNode.table_id == t.id).all()]
    if col_ids:
        rels = db.query(SchemaEdge).filter(
            SchemaEdge.source_column_id.in_(col_ids) | SchemaEdge.target_column_id.in_(col_ids)
        ).all()
        
        for rel in rels:
            src_col = db.query(ColumnNode).filter(ColumnNode.id == rel.source_column_id).first()
            tgt_col = db.query(ColumnNode).filter(ColumnNode.id == rel.target_column_id).first()
            if not src_col or not tgt_col:
                continue
            
            src_tbl = db.query(TableNode).filter(TableNode.id == src_col.table_id).first()
            tgt_tbl = db.query(TableNode).filter(TableNode.id == tgt_col.table_id).first()
            
            if datasource_id and (src_tbl.datasource_id != datasource_id or tgt_tbl.datasource_id != datasource_id):
                continue
            
            rel_type = rel.relationship_type.value if hasattr(rel.relationship_type, 'value') else str(rel.relationship_type)
            
            if include_columns:
                edges.append({
                    "id": f"edge-{rel.id}",
                    "source": f"column-{src_col.id}",
                    "target": f"column-{tgt_col.id}",
                    "type": "smoothstep",
                    "animated": rel.is_inferred,
                    "label": rel.description or rel_type,
                    "data": {"relationship_type": rel_type}
                })
            else:
                edges.append({
                    "id": f"edge-{rel.id}",
                    "source": f"table-{src_tbl.id}",
                    "target": f"table-{tgt_tbl.id}",
                    "type": "smoothstep",
                    "animated": rel.is_inferred,
                    "label": f"{src_col.name} → {tgt_col.name}",
                    "data": {"relationship_type": rel_type, "description": rel.description}
                })
    
    return GraphVisualizationResponse(
        nodes=[GraphNode(**n) for n in nodes],
        edges=[GraphEdge(**e) for e in edges],
        metadata={
            "total_tables": len(tables),
            "total_relationships": len(edges),
            "datasources": [{"id": str(ds.id), "name": ds.name} for ds in datasources],
            "filtered_by_datasource": str(datasource_id) if datasource_id else None,
            "layout": layout,
            "include_columns": include_columns
        }
    )
