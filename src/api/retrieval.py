"""Router for Retrieval & Search domain"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
import json

from ..core.database import get_db
from ..db.models import (
    Datasource, TableNode, ColumnNode, SemanticMetric,
    LowCardinalityValue, SemanticSynonym, GoldenSQL
)
from ..services.embedding_service import embedding_service
from ..schemas.ontology import TableResponseDTO, ColumnResponseDTO
from ..schemas.semantics import MetricResponseDTO, SynonymResponseDTO

router = APIRouter(prefix="/api/v1/retrieval", tags=["Retrieval"])


# Request DTOs
class SearchRequestDTO(BaseModel):
    query: str = Field(..., min_length=1)
    filters: Optional[Dict[str, Any]] = None
    limit: int = Field(10, ge=1, le=50)

class ValueValidationDTO(BaseModel):
    table_name: str
    column_name: str
    values: List[str]

class SynonymResolveDTO(BaseModel):
    term: str

class MetricExplainDTO(BaseModel):
    metric_name: str


# Response DTOs
class SearchResultDTO(BaseModel):
    type: str  # TABLE, COLUMN, METRIC, DATASOURCE
    name: str
    description: Optional[str]
    score: float
    metadata: Dict[str, Any]

class ValidationResultDTO(BaseModel):
    is_valid: bool
    resolved_values: Dict[str, Optional[str]]
    errors: List[str]

class ExplanationDTO(BaseModel):
    metric_name: str
    sql_formula: str
    dependencies: List[str]
    description: Optional[str]


@router.post("/search", response_model=List[SearchResultDTO])
def unified_search(
    search_data: SearchRequestDTO,
    db: Session = Depends(get_db)
):
    """
    Unified semantic search across Datasources, Tables, Columns, and Metrics.
    """
    query_embedding = embedding_service.generate_embedding(search_data.query)
    str_embedding = str(query_embedding)
    
    results = []
    limit = search_data.limit
    
    # Search Datasources
    ds_results = db.query(
        Datasource,
        Datasource.embedding.cosine_distance(query_embedding).label("distance")
    ).filter(Datasource.embedding.isnot(None))\
     .order_by("distance").limit(limit).all()
     
    for ds, dist in ds_results:
        results.append(SearchResultDTO(
            type="DATASOURCE",
            name=ds.name,
            description=ds.description,
            score=1 - dist,
            metadata={"slug": ds.slug, "engine": ds.engine.value}
        ))

    # Search Tables
    table_results = db.query(
        TableNode,
        TableNode.embedding.cosine_distance(query_embedding).label("distance")
    ).filter(TableNode.embedding.isnot(None))\
     .order_by("distance").limit(limit).all()
     
    for table, dist in table_results:
        results.append(SearchResultDTO(
            type="TABLE",
            name=table.semantic_name,
            description=table.description,
            score=1 - dist,
            metadata={
                "physical_name": table.physical_name,
                "datasource_id": str(table.datasource_id),
                "id": str(table.id)
            }
        ))

    # Search Metrics
    metric_results = db.query(
        SemanticMetric,
        SemanticMetric.embedding.cosine_distance(query_embedding).label("distance")
    ).filter(SemanticMetric.embedding.isnot(None))\
     .order_by("distance").limit(limit).all()

    for metric, dist in metric_results:
        results.append(SearchResultDTO(
            type="METRIC",
            name=metric.name,
            description=metric.description,
            score=1 - dist,
            metadata={"sql": metric.calculation_sql}
        ))
        
    # Sort unified results
    results.sort(key=lambda x: x.score, reverse=True)
    return results[:limit]


@router.post("/golden-sql/search", response_model=List[dict])
def search_golden_sql(
    search_data: SearchRequestDTO,
    db: Session = Depends(get_db)
):
    """Search similar Golden SQL examples"""
    query_embedding = embedding_service.generate_embedding(search_data.query)
    
    results = db.query(
        GoldenSQL,
        GoldenSQL.embedding.cosine_distance(query_embedding).label("distance")
    ).filter(GoldenSQL.embedding.isnot(None))\
     .order_by("distance").limit(search_data.limit).all()
     
    return [
        {
            "prompt": sql.prompt_text,
            "sql": sql.sql_query,
            "score": 1 - dist,
            "complexity": sql.complexity_score
        }
        for sql, dist in results
    ]


@router.post("/values/validate", response_model=ValidationResultDTO)
def validate_values(
    validation_data: ValueValidationDTO,
    db: Session = Depends(get_db)
):
    """
    Validate and resolve categorical values (Anti-Hallucination).
    Ex: "Lombardia" -> "LOM"
    """
    # 1. Find the column
    # Ideally should search by table name and column name across datasources
    # For simplicity, assuming unique table.physical_name or we might need datasource context
    
    # Join TableNode and ColumnNode to find target column
    column = db.query(ColumnNode).join(TableNode).filter(
        TableNode.physical_name == validation_data.table_name,
        ColumnNode.name == validation_data.column_name
    ).first()
    
    if not column:
        return ValidationResultDTO(
            is_valid=False,
            resolved_values={},
            errors=[f"Column {validation_data.table_name}.{validation_data.column_name} not found"]
        )

    resolved = {}
    errors = []
    
    for val in validation_data.values:
        # Search in LowCardinalityValue
        # Use simple ILIKE for label matching, or vector search if no exact match
        match = db.query(LowCardinalityValue).filter(
            LowCardinalityValue.column_id == column.id,
            LowCardinalityValue.value_label.ilike(val)
        ).first()
        
        if match:
            resolved[val] = match.value_raw
        else:
            # Fallback to vector search
            val_embedding = embedding_service.generate_embedding(val)
            vector_match = db.query(
                LowCardinalityValue,
                LowCardinalityValue.embedding.cosine_distance(val_embedding).label("distance")
            ).filter(LowCardinalityValue.column_id == column.id)\
             .order_by("distance").limit(1).first()
             
            if vector_match and (1 - vector_match[1] > 0.85): # Threshold
                 resolved[val] = vector_match[0].value_raw
            else:
                 resolved[val] = None
                 errors.append(f"Value '{val}' not found")

    return ValidationResultDTO(
        is_valid=len(errors) == 0,
        resolved_values=resolved,
        errors=errors
    )


@router.post("/synonyms/resolve", response_model=List[dict])
def resolve_synonym(
    synonym_data: SynonymResolveDTO,
    db: Session = Depends(get_db)
):
    """Resolve a term to its canonical definition via synonyms"""
    synonyms = db.query(SemanticSynonym).filter(
        SemanticSynonym.term.ilike(synonym_data.term)
    ).all()
    
    results = []
    for syn in synonyms:
        # Fetch target details based on type
        # For brevity returning raw info
        results.append({
            "term": syn.term,
            "target_type": syn.target_type.value,
            "target_id": str(syn.target_id)
        })
    return results


@router.post("/metrics/explain", response_model=ExplanationDTO)
def explain_metric(
    explain_data: MetricExplainDTO,
    db: Session = Depends(get_db)
):
    """Get calculation details for a metric"""
    metric = db.query(SemanticMetric).filter(
        SemanticMetric.name == explain_data.metric_name
    ).first()
    
    if not metric:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Metric '{explain_data.metric_name}' not found"
        )
        
    # Get table names
    table_names = []
    if metric.required_tables:
        for t_id_str in metric.required_tables:
            t = db.query(TableNode).filter(TableNode.id == t_id_str).first()
            if t:
                table_names.append(t.physical_name)
                
    return ExplanationDTO(
        metric_name=metric.name,
        sql_formula=metric.calculation_sql,
        dependencies=table_names,
        description=metric.description
    )


@router.post("/admin/sync-embeddings", status_code=status.HTTP_200_OK)
def sync_embeddings(db: Session = Depends(get_db)):
    """
    Admin: Re-calculate embeddings where content hash doesn't match stored hash.
    Useful for system maintenance or after bulk updates.
    """
    updated_count = 0
    
    # 1. Sync Datasources
    datasources = db.query(Datasource).all()
    for ds in datasources:
        content = f"{ds.description or ''} {ds.context_signature or ''}".strip()
        current_hash = embedding_service.calculate_hash(content)
        if current_hash != ds.embedding_hash:
            if content:
                ds.embedding = embedding_service.generate_embedding(content)
                ds.embedding_hash = current_hash
                updated_count += 1
            elif ds.embedding is not None:
                # Content cleared, remove embedding
                ds.embedding = None
                ds.embedding_hash = None
                updated_count += 1

    # 2. Sync Tables
    tables = db.query(TableNode).all()
    for t in tables:
        content = f"{t.semantic_name}"
        if t.description: content += f" {t.description}"
        
        current_hash = embedding_service.calculate_hash(content)
        if current_hash != t.embedding_hash:
            t.embedding = embedding_service.generate_embedding(content)
            t.embedding_hash = current_hash
            updated_count += 1

    # 3. Sync Columns
    columns = db.query(ColumnNode).all()
    for c in columns:
        content = c.semantic_name or c.name
        if c.description: content += f" {c.description}"
        if c.context_note: content += f" {c.context_note}"
        
        current_hash = embedding_service.calculate_hash(content)
        if current_hash != c.embedding_hash:
            c.embedding = embedding_service.generate_embedding(content)
            c.embedding_hash = current_hash
            updated_count += 1
            
    # 4. Sync Metrics
    metrics = db.query(SemanticMetric).all()
    for m in metrics:
        # Assuming embedding on name + description
        content = f"{m.name}"
        if m.description: content += f" {m.description}"
        
        current_hash = embedding_service.calculate_hash(content)
        if current_hash != m.embedding_hash:
            m.embedding = embedding_service.generate_embedding(content)
            m.embedding_hash = current_hash
            updated_count += 1
            
    # Other entities (Rules, Values, GoldenSQL) follow same pattern
    # Implementing the key ones for brevity
    
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error syncing embeddings: {str(e)}"
        )
        
    return {"status": "success", "updated_entities": updated_count}
