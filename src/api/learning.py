"""Router for Learning domain"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from ..core.database import get_db
from ..db.models import GoldenSQL, Datasource, AmbiguityLog, GenerationTrace
from ..schemas.learning import (
    GoldenSQLDTO, GoldenSQLResponseDTO, GoldenSQLUpdateDTO,
    AmbiguityLogCreateDTO, AmbiguityLogUpdateDTO, AmbiguityLogResponseDTO,
    GenerationTraceCreateDTO, GenerationTraceUpdateDTO, GenerationTraceResponseDTO
)
from ..services.embedding_service import embedding_service
from ..services.sql_validator import sql_validator
from ..core.logging import get_logger
import re

logger = get_logger("learning")

def slugify(text: str) -> str:
    return re.sub(r'[^a-z0-9]+', '-', text.lower()).strip('-')

router = APIRouter(prefix="/api/v1/learning", tags=["Learning"])


@router.get("/golden-sql", response_model=List[GoldenSQLResponseDTO])
def get_golden_sql(db: Session = Depends(get_db)):
    """Get all golden SQL examples"""
    examples = db.query(GoldenSQL).all()
    return [GoldenSQLResponseDTO.model_validate(e) for e in examples]


@router.post("/golden-sql", response_model=GoldenSQLResponseDTO, status_code=status.HTTP_201_CREATED)
def create_golden_sql(
    golden_sql_data: GoldenSQLDTO,
    db: Session = Depends(get_db)
):
    """
    Insert a correct example for few-shot learning.
    
    - Validates datasource exists
    - Validates SQL syntax
    - Generates embedding for prompt_text (crucial for retrieval)
    """
    # Validate datasource exists
    datasource = db.query(Datasource).filter(Datasource.id == golden_sql_data.datasource_id).first()
    if not datasource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Datasource {golden_sql_data.datasource_id} not found"
        )
    
    # Validate SQL syntax
    # Get dialect from datasource engine
    dialect = datasource.engine.value if hasattr(datasource.engine, 'value') else str(datasource.engine)
    is_valid, error_msg = sql_validator.validate_sql(golden_sql_data.sql_query, dialect=dialect)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid SQL syntax: {error_msg}"
        )
    
    # Generate embedding for prompt_text (crucial for retrieval)
    embedding = embedding_service.generate_embedding(golden_sql_data.prompt_text)
    
    # Create golden SQL
    gsql_slug = slugify(f"gsql-{golden_sql_data.datasource_id}-{str(hash(golden_sql_data.prompt_text))[-8:]}")
    
    golden_sql = GoldenSQL(
        datasource_id=golden_sql_data.datasource_id,
        slug=gsql_slug,
        prompt_text=golden_sql_data.prompt_text,
        sql_query=golden_sql_data.sql_query,
        complexity_score=golden_sql_data.complexity,
        verified=golden_sql_data.verified,
        embedding=embedding
    )
    
    try:
        db.add(golden_sql)
        db.commit()
        db.refresh(golden_sql)
        logger.info(f"Created Golden SQL example (ID: {golden_sql.id}) via Learning API")
        return GoldenSQLResponseDTO.model_validate(golden_sql)
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating golden SQL: {str(e)}"
        )


@router.get("/golden-sql/{golden_sql_id}", response_model=GoldenSQLResponseDTO)
def get_golden_sql_item(
    golden_sql_id: UUID,
    db: Session = Depends(get_db)
):
    """Get a specific golden SQL example"""
    golden_sql = db.query(GoldenSQL).filter(GoldenSQL.id == golden_sql_id).first()
    if not golden_sql:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Golden SQL {golden_sql_id} not found"
        )
    return GoldenSQLResponseDTO.model_validate(golden_sql)


@router.put("/golden-sql/{golden_sql_id}", response_model=GoldenSQLResponseDTO)
def update_golden_sql(
    golden_sql_id: UUID,
    golden_sql_data: GoldenSQLUpdateDTO,
    db: Session = Depends(get_db)
):
    """Update a golden SQL example"""
    golden_sql = db.query(GoldenSQL).filter(GoldenSQL.id == golden_sql_id).first()
    if not golden_sql:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Golden SQL {golden_sql_id} not found"
        )
    
    update_embedding = False
    if golden_sql_data.prompt_text is not None:
        golden_sql.prompt_text = golden_sql_data.prompt_text
        update_embedding = True
    
    if golden_sql_data.sql_query is not None:
        # Validate SQL if changed
        dialect = "postgres" # Default/fallback
        if golden_sql.datasource:
             dialect = golden_sql.datasource.engine.value if hasattr(golden_sql.datasource.engine, 'value') else str(golden_sql.datasource.engine)
             
        is_valid, error_msg = sql_validator.validate_sql(golden_sql_data.sql_query, dialect=dialect)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid SQL syntax: {error_msg}"
            )
        golden_sql.sql_query = golden_sql_data.sql_query
        
    if golden_sql_data.complexity is not None:
        golden_sql.complexity_score = golden_sql_data.complexity
    if golden_sql_data.verified is not None:
        golden_sql.verified = golden_sql_data.verified
        
    if update_embedding:
        golden_sql.embedding = embedding_service.generate_embedding(golden_sql.prompt_text)
    
    try:
        db.commit()
        db.refresh(golden_sql)
        logger.info(f"Updated Golden SQL example: {golden_sql.id} via Learning API")
        return GoldenSQLResponseDTO.model_validate(golden_sql)
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating golden SQL: {str(e)}"
        )


@router.delete("/golden-sql/{golden_sql_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_golden_sql(
    golden_sql_id: UUID,
    db: Session = Depends(get_db)
):
    """Delete a golden SQL example"""
    golden_sql = db.query(GoldenSQL).filter(GoldenSQL.id == golden_sql_id).first()
    if not golden_sql:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Golden SQL {golden_sql_id} not found"
        )
    
    try:
        db.delete(golden_sql)
        db.commit()
        logger.info(f"Deleted Golden SQL: {golden_sql_id} via Learning API")
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting golden SQL: {str(e)}"
        )


# Ambiguity Log Endpoints
@router.get("/ambiguity-logs", response_model=List[AmbiguityLogResponseDTO])
def get_ambiguity_logs(db: Session = Depends(get_db)):
    """Get all ambiguity logs"""
    logs = db.query(AmbiguityLog).all()
    return [AmbiguityLogResponseDTO.model_validate(l) for l in logs]


@router.post("/ambiguity-logs", response_model=AmbiguityLogResponseDTO, status_code=status.HTTP_201_CREATED)
def create_ambiguity_log(
    log_data: AmbiguityLogCreateDTO,
    db: Session = Depends(get_db)
):
    """Create an ambiguity log"""
    log = AmbiguityLog(
        user_query=log_data.user_query,
        detected_ambiguity=log_data.detected_ambiguity,
        user_resolution=log_data.user_resolution
    )
    
    try:
        db.add(log)
        db.commit()
        db.refresh(log)
        logger.info(f"Logged ambiguity resolution (ID: {log.id})")
        return AmbiguityLogResponseDTO.model_validate(log)
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating ambiguity log: {str(e)}"
        )


@router.get("/ambiguity-logs/{log_id}", response_model=AmbiguityLogResponseDTO)
def get_ambiguity_log(
    log_id: UUID,
    db: Session = Depends(get_db)
):
    """Get a specific ambiguity log"""
    log = db.query(AmbiguityLog).filter(AmbiguityLog.id == log_id).first()
    if not log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Log {log_id} not found"
        )
    return AmbiguityLogResponseDTO.model_validate(log)


@router.put("/ambiguity-logs/{log_id}", response_model=AmbiguityLogResponseDTO)
def update_ambiguity_log(
    log_id: UUID,
    log_data: AmbiguityLogUpdateDTO,
    db: Session = Depends(get_db)
):
    """Update an ambiguity log"""
    log = db.query(AmbiguityLog).filter(AmbiguityLog.id == log_id).first()
    if not log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Log {log_id} not found"
        )
    
    if log_data.user_resolution is not None:
        log.user_resolution = log_data.user_resolution
    if log_data.detected_ambiguity is not None:
        log.detected_ambiguity = log_data.detected_ambiguity
    
    try:
        db.commit()
        db.refresh(log)
        logger.info(f"Updated ambiguity log: {log.id}")
        return AmbiguityLogResponseDTO.model_validate(log)
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating ambiguity log: {str(e)}"
        )


@router.delete("/ambiguity-logs/{log_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_ambiguity_log(
    log_id: UUID,
    db: Session = Depends(get_db)
):
    """Delete an ambiguity log"""
    log = db.query(AmbiguityLog).filter(AmbiguityLog.id == log_id).first()
    if not log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Log {log_id} not found"
        )
    
    try:
        db.delete(log)
        db.commit()
        logger.info(f"Deleted ambiguity log: {log_id}")
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting ambiguity log: {str(e)}"
        )


# Generation Trace Endpoints
@router.get("/generation-traces", response_model=List[GenerationTraceResponseDTO])
def get_generation_traces(db: Session = Depends(get_db)):
    """Get all generation traces"""
    traces = db.query(GenerationTrace).all()
    return [GenerationTraceResponseDTO.model_validate(t) for t in traces]


@router.post("/generation-traces", response_model=GenerationTraceResponseDTO, status_code=status.HTTP_201_CREATED)
def create_generation_trace(
    trace_data: GenerationTraceCreateDTO,
    db: Session = Depends(get_db)
):
    """Create a generation trace"""
    trace = GenerationTrace(
        user_prompt=trace_data.user_prompt,
        retrieved_context_snapshot=trace_data.retrieved_context_snapshot,
        generated_sql=trace_data.generated_sql,
        error_message=trace_data.error_message,
        user_feedback=trace_data.user_feedback
    )
    
    try:
        db.add(trace)
        db.commit()
        db.refresh(trace)
        return GenerationTraceResponseDTO.model_validate(trace)
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating generation trace: {str(e)}"
        )


@router.get("/generation-traces/{trace_id}", response_model=GenerationTraceResponseDTO)
def get_generation_trace(
    trace_id: UUID,
    db: Session = Depends(get_db)
):
    """Get a specific generation trace"""
    trace = db.query(GenerationTrace).filter(GenerationTrace.id == trace_id).first()
    if not trace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Trace {trace_id} not found"
        )
    return GenerationTraceResponseDTO.model_validate(trace)


@router.put("/generation-traces/{trace_id}", response_model=GenerationTraceResponseDTO)
def update_generation_trace(
    trace_id: UUID,
    trace_data: GenerationTraceUpdateDTO,
    db: Session = Depends(get_db)
):
    """Update a generation trace"""
    trace = db.query(GenerationTrace).filter(GenerationTrace.id == trace_id).first()
    if not trace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Trace {trace_id} not found"
        )
    
    if trace_data.user_feedback is not None:
        trace.user_feedback = trace_data.user_feedback
    if trace_data.error_message is not None:
        trace.error_message = trace_data.error_message
    if trace_data.generated_sql is not None:
        trace.generated_sql = trace_data.generated_sql
    
    try:
        db.commit()
        db.refresh(trace)
        return GenerationTraceResponseDTO.model_validate(trace)
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating generation trace: {str(e)}"
        )


@router.delete("/generation-traces/{trace_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_generation_trace(
    trace_id: UUID,
    db: Session = Depends(get_db)
):
    """Delete a generation trace"""
    trace = db.query(GenerationTrace).filter(GenerationTrace.id == trace_id).first()
    if not trace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Trace {trace_id} not found"
        )
    
    try:
        db.delete(trace)
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting generation trace: {str(e)}"
        )
