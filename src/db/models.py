"""SQLAlchemy database models"""
from sqlalchemy import (
    Column, String, Text, Boolean, Integer, ForeignKey,
    JSON, DateTime, Enum as SQLEnum
)
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector
import uuid
from enum import Enum as PyEnum
from ..core.database import Base





# Enums
class SQLEngineType(PyEnum):
    """SQL Engine types"""
    POSTGRES = "postgres"
    BIGQUERY = "bigquery"
    SNOWFLAKE = "snowflake"
    TSQL = "tsql"
    MYSQL = "mysql"


class RelationshipType(PyEnum):
    """Relationship types between columns"""
    ONE_TO_ONE = "ONE_TO_ONE"
    ONE_TO_MANY = "ONE_TO_MANY"
    MANY_TO_MANY = "MANY_TO_MANY"


class SynonymTargetType(PyEnum):
    """Target types for synonyms"""
    TABLE = "TABLE"
    COLUMN = "COLUMN"
    METRIC = "METRIC"
    VALUE = "VALUE"


# Core Registry Models
class Datasource(Base):
    """
    Physical datasource definition.
    The physical query perimeter.
    """
    __tablename__ = "datasources"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, unique=True, doc="Identificativo mnemonico (es. 'Sales DWH Prod')")
    slug = Column(String(255), nullable=False, unique=True, doc="Human-readable identifier")
    description = Column(Text, nullable=True, doc="Description of the datasource")
    engine = Column(SQLEnum(SQLEngineType), nullable=False, doc="Il dialetto SQL target")
    context_signature = Column(Text, nullable=True, doc="Text blob with keywords, table names, key metrics")
    embedding = Column(Vector(1536), nullable=True, doc="Embedding of description + context_signature")
    embedding_hash = Column(String(64), nullable=True, doc="Hash of content used for embedding to track changes")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    tables = relationship("TableNode", back_populates="datasource", cascade="all, delete-orphan")


class TableNode(Base):
    """
    Table nodes in the knowledge graph.
    Main nodes of the knowledge graph.
    """
    __tablename__ = "table_nodes"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    datasource_id = Column(UUID(as_uuid=True), ForeignKey("datasources.id"), nullable=False)
    physical_name = Column(String(255), nullable=False, doc="Nome reale nel DB (t_orders_v2)")
    semantic_name = Column(String(255), nullable=False, doc="Nome 'pulito' per l'LLM (Orders Table)")
    description = Column(Text, nullable=True, doc="Metadato curato descrittivo. Driver primario per il retrieval vettoriale macro")
    ddl_context = Column(Text, nullable=True, doc="Lo statement CREATE TABLE minimizzato")
    embedding = Column(Vector(1536), nullable=True, doc="Embedding denso di (Semantic Name + Description)")
    embedding_hash = Column(String(64), nullable=True, doc="Hash of content used for embedding")
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    datasource = relationship("Datasource", back_populates="tables")
    columns = relationship("ColumnNode", back_populates="table", cascade="all, delete-orphan")
    
    # Note: Unique constraint for (datasource_id, physical_name) should be added via Alembic migration


class ColumnNode(Base):
    """
    Column attributes.
    The atomic attributes.
    """
    __tablename__ = "column_nodes"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    table_id = Column(UUID(as_uuid=True), ForeignKey("table_nodes.id"), nullable=False)
    name = Column(String(255), nullable=False, doc="Nome fisico (usr_id)")
    semantic_name = Column(String(255), nullable=True)
    data_type = Column(String(100), nullable=False, doc="Tipo nativo (VARCHAR, INT)")
    is_primary_key = Column(Boolean, default=False, nullable=False, doc="Critico per identificare le entità uniche")
    description = Column(Text, nullable=True)
    context_note = Column(Text, nullable=True)
    embedding = Column(Vector(1536), nullable=True, doc="Embedding del nome e dei metadati per la ricerca fine")
    embedding_hash = Column(String(64), nullable=True, doc="Hash of content used for embedding")
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    table = relationship("TableNode", back_populates="columns")
    source_relationships = relationship(
        "SchemaEdge",
        foreign_keys="SchemaEdge.source_column_id",
        back_populates="source_column"
    )
    target_relationships = relationship(
        "SchemaEdge",
        foreign_keys="SchemaEdge.target_column_id",
        back_populates="target_column"
    )
    context_rules = relationship("ColumnContextRule", back_populates="column", cascade="all, delete-orphan")
    nominal_values = relationship("LowCardinalityValue", back_populates="column", cascade="all, delete-orphan")


class SchemaEdge(Base):
    """
    Table relationships (topology).
    The highways of data. Defines how tables can be legally linked.
    """
    __tablename__ = "schema_edges"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_column_id = Column(UUID(as_uuid=True), ForeignKey("column_nodes.id"), nullable=False)
    target_column_id = Column(UUID(as_uuid=True), ForeignKey("column_nodes.id"), nullable=False)
    relationship_type = Column(SQLEnum(RelationshipType), nullable=False, doc="1:1, 1:N, N:N")
    is_inferred = Column(Boolean, default=False, nullable=False, doc="False se esiste una FK fisica, True se virtuale")
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    source_column = relationship("ColumnNode", foreign_keys=[source_column_id], back_populates="source_relationships")
    target_column = relationship("ColumnNode", foreign_keys=[target_column_id], back_populates="target_relationships")


# Semantic Layer Models
class SemanticMetric(Base):
    """
    Business KPI definitions.
    Authoritative definition of business KPIs. Prevents LLM hallucinations.
    """
    __tablename__ = "semantic_metrics"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, unique=True, doc="Es. 'ARR - Annual Recurring Revenue'")
    description = Column(Text, nullable=True, doc="Spiegazione di business per il retrieval")
    calculation_sql = Column(Text, nullable=False, doc="Lo snippet SQL puro")
    required_tables = Column(JSON, nullable=True, doc="Lista delle tabelle fisiche necessarie")
    filter_condition = Column(Text, nullable=True)
    embedding = Column(Vector(1536), nullable=True, doc="Vettore del concetto di business")
    embedding_hash = Column(String(64), nullable=True, doc="Hash of content used for embedding")
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class SemanticSynonym(Base):
    """
    Domain vocabulary mapping.
    Translation dictionary Domain <-> Data.
    """
    __tablename__ = "semantic_synonyms"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    term = Column(String(255), nullable=False, doc="Il termine usato dagli umani")
    target_type = Column(SQLEnum(SynonymTargetType), nullable=False, doc="TABLE, COLUMN, METRIC, VALUE")
    target_id = Column(UUID(as_uuid=True), nullable=False, doc="Riferimento all'entità fisica o logica mappata")
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Note: Unique constraint should be added via Alembic migration


# Context & Value Models
class ColumnContextRule(Base):
    """
    Business rules for column interpretation.
    Tribal Knowledge.
    """
    __tablename__ = "column_context_rules"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    column_id = Column(UUID(as_uuid=True), ForeignKey("column_nodes.id"), nullable=False)
    rule_text = Column(Text, nullable=False, doc="Istruzione esplicita")
    embedding = Column(Vector(1536), nullable=True, doc="Permette di recuperare la regola solo quando pertinente")
    embedding_hash = Column(String(64), nullable=True, doc="Hash of content used for embedding")
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    column = relationship("ColumnNode", back_populates="context_rules")


class LowCardinalityValue(Base):
    """
    Nominal value mappings.
    Vector lookup table for categorical values.
    """
    __tablename__ = "low_cardinality_values"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    column_id = Column(UUID(as_uuid=True), ForeignKey("column_nodes.id"), nullable=False)
    value_raw = Column(String(255), nullable=False, doc="Il dato reale nel DB")
    value_label = Column(String(255), nullable=False, doc="Etichetta semantica/estesa")
    embedding = Column(Vector(1536), nullable=True, doc="Vettore dell'etichetta")
    embedding_hash = Column(String(64), nullable=True, doc="Hash of content used for embedding")
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    column = relationship("ColumnNode", back_populates="nominal_values")
    
    # Note: Unique constraint should be added via Alembic migration


# Learning Models
class GoldenSQL(Base):
    """
    Few-shot examples for learning.
    Long-term memory of perfect examples (Vanna style).
    """
    __tablename__ = "golden_sql"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    datasource_id = Column(UUID(as_uuid=True), ForeignKey("datasources.id"), nullable=False)
    prompt_text = Column(Text, nullable=False, doc="Domanda in linguaggio naturale")
    sql_query = Column(Text, nullable=False, doc="Query SQL validata 'Gold Standard'")
    complexity_score = Column(Integer, nullable=False, default=1, doc="1-5. Usato per selezionare esempi di difficoltà analoga")
    verified = Column(Boolean, default=True, nullable=False)
    embedding = Column(Vector(1536), nullable=True, doc="Embedding della domanda")
    embedding_hash = Column(String(64), nullable=True, doc="Hash of content used for embedding")
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    datasource = relationship("Datasource")


class AmbiguityLog(Base):
    """
    Log of ambiguous queries for improvement.
    Registry of uncertainties for RLHF.
    """
    __tablename__ = "ambiguity_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_query = Column(Text, nullable=False, doc="La domanda originale")
    detected_ambiguity = Column(JSON, nullable=True, doc="Le opzioni rilevate")
    user_resolution = Column(Text, nullable=True, doc="La scelta effettuata dall'utente")
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class GenerationTrace(Base):
    """
    Orchestration and observability.
    Black box of the generation process.
    """
    __tablename__ = "generation_traces"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_prompt = Column(Text, nullable=False)
    retrieved_context_snapshot = Column(JSON, nullable=True)
    generated_sql = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    user_feedback = Column(Integer, nullable=True)  # -1, 0, 1
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
