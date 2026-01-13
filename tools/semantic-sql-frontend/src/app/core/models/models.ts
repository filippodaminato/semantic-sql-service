export enum SQLEngineType {
    POSTGRES = "postgres",
    BIGQUERY = "bigquery",
    SNOWFLAKE = "snowflake",
    TSQL = "tsql",
    MYSQL = "mysql"
}

export enum RelationshipType {
    ONE_TO_ONE = "ONE_TO_ONE",
    ONE_TO_MANY = "ONE_TO_MANY",
    MANY_TO_ONE = "MANY_TO_ONE",
    MANY_TO_MANY = "MANY_TO_MANY"
}

export enum SynonymTargetType {
    TABLE = "TABLE",
    COLUMN = "COLUMN",
    METRIC = "METRIC",
    VALUE = "VALUE"
}

export interface Datasource {
    id: string;
    name: string;
    slug: string;
    description?: string;
    engine: SQLEngineType;
    context_signature?: string;
    created_at?: string;
    updated_at?: string;
}

export interface DatasourceUpdate {
    name?: string;
    description?: string;
    context_signature?: string;
    connection_string?: string;
}

export interface TableNode {
    id: string;
    datasource_id: string;
    physical_name: string;
    semantic_name: string;
    description?: string;
    ddl_context?: string;
    columns?: ColumnNode[];
    created_at?: string;
    updated_at?: string;
}

export interface ColumnNode {
    id: string;
    table_id: string;
    name: string;
    semantic_name?: string;
    data_type: string;
    is_primary_key: boolean;
    description?: string;
    context_note?: string;
    created_at?: string;
    updated_at?: string;
}

export interface SchemaEdge {
    id: string;
    source_column_id: string;
    target_column_id: string;
    relationship_type: RelationshipType;
    is_inferred: boolean;
    created_at?: string;
}

export interface SemanticMetric {
    id: string;
    name: string;
    description?: string;
    calculation_sql: string;
    required_tables?: string[];
    filter_condition?: string;
    created_at?: string;
    updated_at?: string;
}

export interface SemanticSynonym {
    id: string;
    term: string;
    target_type: SynonymTargetType;
    target_id: string;
    created_at?: string;
}

// Context & Rules
export interface ContextRule {
    id: string;
    rule_text: string;
    scope: string; // e.g. "GLOBAL", "TABLE:xyz"
    created_at?: string;
}

export interface NominalValue {
    id: string;
    column_id: string;
    value: string;
    synonyms?: string[];
    created_at?: string;
}

// Learning & Feedback
export interface GoldenSQL {
    id: string;
    question: string;
    sql: string;
    verified: boolean;
    created_at?: string;
    updated_at?: string;
}

export interface AmbiguityLog {
    id: string;
    question: string;
    detected_ambiguities: string[];
    user_clarification?: string;
    created_at?: string;
}

export interface GenerationTrace {
    id: string;
    request_id: string;
    step: string;
    details: any;
    created_at?: string;
}

// Graph Visualization Types
export interface GraphNodeData {
    label: string;
    physical_name?: string;
    semantic_name?: string;
    description?: string;
    datasource?: string;
    datasource_id?: string;
    column_count?: number;
    columns?: string[];
    primary_keys?: string[];
}

export interface GraphNode {
    id: string;
    type: string;
    data: GraphNodeData;
    position: { x: number; y: number };
    parentNode?: string;
}

export interface GraphEdgeData {
    relationship_type: string;
    is_inferred: boolean;
    description?: string;
    source_column: string;
    target_column: string;
    source_table?: string;
    target_table?: string;
}

export interface GraphEdge {
    id: string;
    source: string;
    target: string;
    type: string;
    animated: boolean;
    label: string;
    data: GraphEdgeData;
}

export interface GraphVisualizationResponse {
    nodes: GraphNode[];
    edges: GraphEdge[];
    metadata: {
        total_tables: number;
        total_relationships: number;
        datasources: { id: string; name: string }[];
        filtered_by_datasource?: string;
        layout: string;
        include_columns: boolean;
    };
}

// API Response Types
export interface OmniSearchResponse {
    relevant_tables: TableNode[];
    context: string;
}

export interface GraphExpandResponse {
    nodes: any[];
    edges: any[];
}

export interface MetricValidationResponse {
    is_valid: boolean;
    error_message?: string;
    sql_preview?: string;
}
