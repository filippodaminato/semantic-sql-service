"""
SQLAlchemy database models for Semantic SQL Engine.

This module defines all database models using SQLAlchemy's declarative base.
Models are organized into domains:
- Core Registry: Physical ontology (datasources, tables, columns, relationships)
- Semantic Layer: Business semantics (metrics, synonyms)
- Context & Values: Contextual intelligence (nominal values, rules)
- Learning: Few-shot examples (golden SQL)

All models that support semantic search inherit from SearchableMixin,
which provides automatic embedding generation and unified search capabilities.
"""

from sqlalchemy import (
    Column, String, Text, Boolean, Integer, ForeignKey,
    JSON, DateTime, Enum as SQLEnum
)
from sqlalchemy.dialects.postgresql import UUID, TSVECTOR, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.schema import Computed
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector
import uuid
from enum import Enum as PyEnum
from ..core.database import Base
from ..core.searchable_mixin import SearchableMixin


# ============================================================================
# Enums
# ============================================================================

class SQLEngineType(PyEnum):
    """
    SQL engine/dialect types supported by the system.
    
    The engine type determines:
    - SQL syntax validation rules
    - Query generation dialect
    - Schema scanning behavior
    
    Values:
        POSTGRES: PostgreSQL database
        BIGQUERY: Google BigQuery
        SNOWFLAKE: Snowflake data warehouse
        TSQL: Microsoft SQL Server (T-SQL)
        MYSQL: MySQL database
    """
    POSTGRES = "postgres"
    BIGQUERY = "bigquery"
    SNOWFLAKE = "snowflake"
    TSQL = "tsql"
    MYSQL = "mysql"


class RelationshipType(PyEnum):
    """
    Types of relationships between database columns.
    
    Used to define JOIN relationships in the schema graph.
    These relationships are critical for SQL generation to understand
    how tables can be legally joined.
    
    Values:
        ONE_TO_ONE: Each source row maps to exactly one target row
        ONE_TO_MANY: Each source row maps to multiple target rows (most common)
        MANY_TO_MANY: Multiple source rows map to multiple target rows
                      (requires junction table)
    """
    ONE_TO_ONE = "ONE_TO_ONE"
    ONE_TO_MANY = "ONE_TO_MANY"
    MANY_TO_MANY = "MANY_TO_MANY"


class SynonymTargetType(PyEnum):
    """
    Target entity types for semantic synonyms.
    
    Synonyms map human language terms to specific entities in the system.
    The target type determines which entity the synonym refers to.
    
    Values:
        TABLE: Synonym maps to a table
        COLUMN: Synonym maps to a column
        METRIC: Synonym maps to a semantic metric
        VALUE: Synonym maps to a nominal value
    """
    TABLE = "TABLE"
    COLUMN = "COLUMN"
    METRIC = "METRIC"
    VALUE = "VALUE"


# ============================================================================
# Core Registry Models (Physical Ontology)
# ============================================================================


# Core Registry Models
class Datasource(SearchableMixin, Base):
    """
    Physical datasource definition representing a database connection.
    
    A datasource defines the physical query perimeter - it represents a specific
    database instance and determines the SQL dialect used for query generation.
    All tables must belong to a datasource.
    
    The datasource serves as the root of the ontology hierarchy:
    Datasource -> Tables -> Columns -> Relationships
    
    Attributes:
        id: Unique identifier (UUID)
        name: Human-readable name (e.g., "Sales DWH Prod")
        slug: URL-friendly identifier (auto-generated from name)
        description: Description of the datasource and its purpose
        engine: SQL dialect (postgres, bigquery, snowflake, etc.)
        context_signature: Keywords, table names, and key metrics for context
        embedding: Vector embedding for semantic search (generated from description + context_signature)
        embedding_hash: SHA-256 hash for caching (prevents unnecessary regeneration)
        search_vector: PostgreSQL TSVECTOR for full-text search (computed column)
        created_at: Timestamp of creation
        updated_at: Timestamp of last update
    
    Relationships:
        tables: One-to-many relationship with TableNode (cascade delete)
    
    Example:
        ```python
        datasource = Datasource(
            name="Sales DWH Prod",
            engine=SQLEngineType.POSTGRES,
            description="Production sales data warehouse",
            context_signature="sales, transactions, e-commerce, revenue"
        )
        ```
    
    Note:
        - Inherits from SearchableMixin for semantic search capabilities
        - search_vector is computed from description + context_signature
        - Embedding is automatically generated on save if content changes
    """
    __tablename__ = "datasources"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, unique=True, doc="Human-readable name (e.g., 'Sales DWH Prod')")
    slug = Column(String(255), nullable=False, unique=True, doc="URL-friendly identifier for API endpoints")
    description = Column(Text, nullable=True, doc="Description of the datasource and its purpose")
    engine = Column(SQLEnum(SQLEngineType), nullable=False, doc="SQL dialect (postgres, bigquery, snowflake, etc.)")
    context_signature = Column(
        Text,
        nullable=True,
        doc="Text blob with keywords, table names, key metrics for semantic context"
    )
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    tables = relationship("TableNode", back_populates="datasource", cascade="all, delete-orphan")

    # Computed full-text search vector (PostgreSQL TSVECTOR)
    # Automatically updated when description or context_signature changes
    search_vector = Column(
        TSVECTOR,
        Computed("to_tsvector('simple', description || ' ' || context_signature)", persisted=True)
    )

    def get_search_content(self) -> str:
        """
        Get text content for embedding generation and search.
        
        Returns:
            str: Concatenated description and context_signature
        """
        parts = [self.description, self.context_signature]
        return " ".join([p for p in parts if p]).strip()


class TableNode(SearchableMixin, Base):
    """
    Table node representing a database table in the knowledge graph.
    
    TableNode is a core entity that represents a physical database table
    with semantic metadata. It serves as the main node in the knowledge graph,
    connecting to columns (attributes) and relationships (edges).
    
    The table has both physical and semantic representations:
    - physical_name: Actual table name in the database (e.g., "t_orders_v2")
    - semantic_name: Human-readable name for LLM understanding (e.g., "Orders Table")
    
    Attributes:
        id: Unique identifier (UUID)
        datasource_id: Foreign key to Datasource
        physical_name: Actual table name in the database
        slug: URL-friendly identifier
        semantic_name: Human-readable name for semantic search
        description: Detailed description (primary driver for vector retrieval)
        ddl_context: Minimal CREATE TABLE statement for LLM context
        embedding: Vector embedding for semantic search
        embedding_hash: SHA-256 hash for caching
        search_vector: PostgreSQL TSVECTOR for full-text search (computed)
        created_at: Timestamp of creation
        updated_at: Timestamp of last update
    
    Relationships:
        datasource: Many-to-one relationship with Datasource
        columns: One-to-many relationship with ColumnNode (cascade delete)
    
    Example:
        ```python
        table = TableNode(
            datasource_id=datasource.id,
            physical_name="t_sales_2024",
            semantic_name="Sales Transactions",
            description="Tabella principale contenente tutte le transazioni e-commerce",
            ddl_context="CREATE TABLE t_sales_2024 (id INT, amount DECIMAL(10,2))"
        )
        ```
    
    Note:
        - Unique constraint: (datasource_id, physical_name) should be enforced via Alembic migration
        - Embedding is generated from semantic_name + description
        - Inherits SearchableMixin for unified search capabilities
    """
    __tablename__ = "table_nodes"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    datasource_id = Column(UUID(as_uuid=True), ForeignKey("datasources.id"), nullable=False)
    physical_name = Column(String(255), nullable=False, doc="Actual table name in database (e.g., 't_orders_v2')")
    slug = Column(String(255), nullable=False, unique=True, index=True, doc="URL-friendly identifier")
    semantic_name = Column(String(255), nullable=False, doc="Human-readable name for LLM (e.g., 'Orders Table')")
    description = Column(
        Text,
        nullable=True,
        doc="Detailed description. Primary driver for vector retrieval in semantic search"
    )
    ddl_context = Column(
        Text,
        nullable=True,
        doc="Minimal CREATE TABLE statement. Provides exact structure for LLM during SQL generation"
    )
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    datasource = relationship("Datasource", back_populates="tables")
    columns = relationship("ColumnNode", back_populates="table", cascade="all, delete-orphan")

    # Computed full-text search vector
    search_vector = Column(
        TSVECTOR,
        Computed("to_tsvector('simple', semantic_name || ' ' || description)", persisted=True)
    )

    def get_search_content(self) -> str:
        """
        Get text content for embedding generation and search.
        
        Returns:
            str: Concatenated semantic_name and description
        """
        parts = [self.semantic_name, self.description]
        return " ".join([p for p in parts if p]).strip()
    
    # Note: Unique constraint for (datasource_id, physical_name) should be added via Alembic migration


class ColumnNode(SearchableMixin, Base):
    """
    Column node representing a database column (atomic attribute).
    
    ColumnNode represents a single column in a database table. It contains
    both physical metadata (name, data type) and semantic metadata
    (semantic_name, description, context_note) for intelligent SQL generation.
    
    Columns are the atomic building blocks of the knowledge graph and can
    participate in relationships (foreign keys) for JOIN path discovery.
    
    Attributes:
        id: Unique identifier (UUID)
        table_id: Foreign key to TableNode
        name: Physical column name in database (e.g., "usr_id")
        slug: URL-friendly identifier
        semantic_name: Human-readable name (e.g., "User ID")
        data_type: Native SQL data type (e.g., "VARCHAR(255)", "INT", "DECIMAL(10,2)")
        is_primary_key: Whether this column is a primary key (critical for entity identification)
        description: Column description for semantic search
        context_note: Additional context (e.g., "NULL means transaction failed")
        embedding: Vector embedding for semantic search
        embedding_hash: SHA-256 hash for caching
        search_vector: PostgreSQL TSVECTOR for full-text search (computed)
        created_at: Timestamp of creation
        updated_at: Timestamp of last update
    
    Relationships:
        table: Many-to-one relationship with TableNode
        source_relationships: Relationships where this column is the source (foreign key)
        target_relationships: Relationships where this column is the target (referenced key)
        context_rules: Business rules for column interpretation
        nominal_values: Low-cardinality value mappings for categorical columns
    
    Example:
        ```python
        column = ColumnNode(
            table_id=table.id,
            name="amount_total",
            semantic_name="Importo Totale",
            data_type="DECIMAL(10,2)",
            is_primary_key=False,
            description="Importo totale della transazione",
            context_note="Include IVA. Se null, transazione fallita."
        )
        ```
    
    Note:
        - Embedding is generated from semantic_name/name + description + context_note
        - Primary key columns are critical for entity identification in SQL generation
        - Inherits SearchableMixin for unified search capabilities
    """
    __tablename__ = "column_nodes"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    table_id = Column(UUID(as_uuid=True), ForeignKey("table_nodes.id"), nullable=False)
    name = Column(String(255), nullable=False, doc="Physical column name in database (e.g., 'usr_id')")
    slug = Column(String(255), nullable=False, unique=True, index=True, doc="URL-friendly identifier")
    semantic_name = Column(String(255), nullable=True, doc="Human-readable name (e.g., 'User ID')")
    data_type = Column(String(100), nullable=False, doc="Native SQL data type (e.g., 'VARCHAR(255)', 'INT')")
    is_primary_key = Column(
        Boolean,
        default=False,
        nullable=False,
        doc="Whether this column is a primary key. Critical for entity identification."
    )
    description = Column(Text, nullable=True, doc="Column description for semantic search")
    context_note = Column(
        Text,
        nullable=True,
        doc="Additional context (e.g., 'NULL means transaction failed', business rules)"
    )
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    table = relationship("TableNode", back_populates="columns")
    source_relationships = relationship(
        "SchemaEdge",
        foreign_keys="SchemaEdge.source_column_id",
        back_populates="source_column",
        cascade="all, delete-orphan"
    )
    target_relationships = relationship(
        "SchemaEdge",
        foreign_keys="SchemaEdge.target_column_id",
        back_populates="target_column",
        cascade="all, delete-orphan"
    )
    context_rules = relationship("ColumnContextRule", back_populates="column", cascade="all, delete-orphan")
    nominal_values = relationship("LowCardinalityValue", back_populates="column", cascade="all, delete-orphan")

    search_vector = Column(
        TSVECTOR,
        Computed("to_tsvector('simple', semantic_name || ' ' || description || ' ' || context_note)", persisted=True)
    )

    def get_search_content(self) -> str:
        parts = [self.semantic_name or self.name, self.description, self.context_note]
        return " ".join([p for p in parts if p]).strip()


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
    description = Column(Text, nullable=True, doc="Descrizione semantica della relazione, e.g. 'Cliente che ha effettuato l'ordine'")
    context_note = Column(Text, nullable=True, doc="Note aggiuntive di contesto, e.g. why this relationship exists")
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    source_column = relationship("ColumnNode", foreign_keys=[source_column_id], back_populates="source_relationships")
    target_column = relationship("ColumnNode", foreign_keys=[target_column_id], back_populates="target_relationships")


# Semantic Layer Models
class SemanticMetric(SearchableMixin, Base):
    """
    Business KPI definitions.
    Authoritative definition of business KPIs. Prevents LLM hallucinations.
    """
    __tablename__ = "semantic_metrics"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    datasource_id = Column(UUID(as_uuid=True), ForeignKey("datasources.id"), nullable=False, doc="Datasource this metric belongs to. Required.")
    name = Column(String(255), nullable=False, unique=True, doc="Es. 'ARR - Annual Recurring Revenue'")
    slug = Column(String(255), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True, doc="Spiegazione di business per il retrieval")
    calculation_sql = Column(Text, nullable=False, doc="Lo snippet SQL puro")
    required_tables = Column(JSONB, nullable=True, doc="Lista delle tabelle fisiche necessarie")
    filter_condition = Column(Text, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    datasource = relationship("Datasource")

    search_vector = Column(
        TSVECTOR,
        Computed("to_tsvector('simple', name || ' ' || description)", persisted=True)
    )

    def get_search_content(self) -> str:
        parts = [self.name, self.description]
        return " ".join([p for p in parts if p]).strip()


class SemanticSynonym(SearchableMixin, Base):
    """
    Domain vocabulary mapping.
    Translation dictionary Domain <-> Data.
    """
    __tablename__ = "semantic_synonyms"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    #datasource_id
    term = Column(String(255), nullable=False, doc="Il termine usato dagli umani")
    slug = Column(String(255), nullable=False, unique=True, index=True)
    target_type = Column(SQLEnum(SynonymTargetType), nullable=False, doc="TABLE, COLUMN, METRIC, VALUE")
    target_id = Column(UUID(as_uuid=True), nullable=False, doc="Riferimento all'entità fisica o logica mappata")
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Note: Unique constraint should be added via Alembic migration

    search_vector = Column(
        TSVECTOR,
        Computed("to_tsvector('simple', term)", persisted=True)
    )

    def get_search_content(self) -> str:
        return (self.term or "").strip()


# Context & Value Models
class ColumnContextRule(SearchableMixin, Base):
    """
    Business rules for column interpretation.
    Tribal Knowledge.
    """
    __tablename__ = "column_context_rules"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    column_id = Column(UUID(as_uuid=True), ForeignKey("column_nodes.id"), nullable=False)
    slug = Column(String(255), nullable=False, unique=True, index=True)
    rule_text = Column(Text, nullable=False, doc="Istruzione esplicita")
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    column = relationship("ColumnNode", back_populates="context_rules")

    search_vector = Column(
        TSVECTOR,
        Computed("to_tsvector('simple', rule_text)", persisted=True)
    )

    def get_search_content(self) -> str:
        return (self.rule_text or "").strip()


class LowCardinalityValue(SearchableMixin, Base):
    """
    Nominal value mappings.
    Vector lookup table for categorical values.
    """
    __tablename__ = "low_cardinality_values"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    column_id = Column(UUID(as_uuid=True), ForeignKey("column_nodes.id"), nullable=False)
    value_raw = Column(String(255), nullable=False, doc="Il dato reale nel DB")
    slug = Column(String(255), nullable=False, unique=True, index=True)
    value_label = Column(String(255), nullable=False, doc="Etichetta semantica/estesa")
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    column = relationship("ColumnNode", back_populates="nominal_values")
    
    # Note: Unique constraint should be added via Alembic migration

    # Override: Solo FTS per valori nominali (opzionale, ma default hybrid va bene)
    _search_mode = "fts_only"

    search_vector = Column(
        TSVECTOR,
        Computed("to_tsvector('simple', value_label)", persisted=True)
    )

    def get_search_content(self) -> str:
        return (self.value_label or "").strip()


# Learning Models
class GoldenSQL(SearchableMixin, Base):
    """
    Few-shot examples for learning.
    Long-term memory of perfect examples (Vanna style).
    """
    __tablename__ = "golden_sql"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    datasource_id = Column(UUID(as_uuid=True), ForeignKey("datasources.id"), nullable=False)
    prompt_text = Column(Text, nullable=False, doc="Domanda in linguaggio naturale")
    slug = Column(String(255), nullable=False, unique=True, index=True)
    sql_query = Column(Text, nullable=False, doc="Query SQL validata 'Gold Standard'")
    complexity_score = Column(Integer, nullable=False, default=1, doc="1-5. Usato per selezionare esempi di difficoltà analoga")
    verified = Column(Boolean, default=True, nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    datasource = relationship("Datasource")

    search_vector = Column(
        TSVECTOR,
        Computed("to_tsvector('simple', prompt_text)", persisted=True)
    )

    def get_search_content(self) -> str:
        return (self.prompt_text or "").strip()


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
