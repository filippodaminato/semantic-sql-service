export interface Datasource {
    id: string;
    name: string;
    slug: string;
    engine: string;
    description?: string;
    context_signature?: string;
    created_at: string;
}

export interface DatasourceCreate {
    name: string;
    slug: string;
    engine: string;
    description?: string;
    context_signature?: string;
    connection_string?: string;
}

export interface RefreshIndexResponse {
    updated_count: number;
    entities: string[];
}

export interface Table {
    id: string;
    datasource_id: string;
    physical_name: string;
    slug: string;
    semantic_name: string;
    description?: string;
    ddl_context?: string;
    created_at: string;
    columns: Column[];
    context_rules?: ContextRule[];
    nominal_values?: NominalValue[];
}

export interface Column {
    id: string;
    table_id: string;
    name: string;
    slug: string;
    data_type: string;
    is_primary_key: boolean;
    semantic_name?: string;
    description?: string;
    context_note?: string;
}

export interface TableCreate {
    datasource_id: string;
    physical_name: string;
    slug: string;
    semantic_name: string;
    description?: string;
    columns?: Partial<Column>[];
}

export interface Relationship {
    id: string;
    source_column_id: string;
    target_column_id: string;
    relationship_type: 'ONE_TO_ONE' | 'ONE_TO_MANY' | 'MANY_TO_MANY';
    description?: string;
}

export interface Metric {
    id: string;
    name: string;
    slug: string;
    description?: string;
    sql_expression: string;
    required_table_ids: string[];
    filter_condition?: string;
}

export interface MetricCreate {
    name: string;
    slug: string;
    description?: string;
    sql_expression: string;
    required_table_ids: string[];
    filter_condition?: string;
}

export interface Synonym {
    id: string;
    term: string;
    slug: string;
    target_type: 'TABLE' | 'COLUMN' | 'METRIC';
    target_id: string;
}

export interface SynonymCreate {
    term: string;
    slug: string;
    target_type: 'TABLE' | 'COLUMN' | 'METRIC';
    target_id: string;
}

export interface ContextRule {
    id: string;
    column_id: string;
    slug: string;
    column_name?: string;
    rule_text: string;
}

export interface ContextRuleCreate {
    column_id: string;
    slug: string;
    rule_text: string;
}

export interface NominalValue {
    id: string;
    column_id?: string;
    slug: string;
    column_name?: string;
    raw: string;
    label: string;
}

export interface NominalValueCreate {
    raw: string;
    slug: string;
    label: string;
}

export interface GoldenSQL {
    id: string;
    datasource_id: string;
    prompt_text: string;
    slug: string;
    sql_query: string;
    complexity: number;
    verified: boolean;
    complexity_score: number;
    created_at?: string;
}

export interface GoldenSQLCreate {
    datasource_id: string;
    prompt_text: string;
    slug: string;
    sql_query: string;
    complexity: number;
    verified?: boolean;
}
