export interface SearchRequest {
    query?: string;
    filters?: SearchFilters;
    limit?: number;
}

export interface SearchFilters {
    entity_types?: ('DATASOURCE' | 'TABLE' | 'COLUMN' | 'METRIC')[];
    datasource_slug?: string;
    parent_id?: string;
}

export interface SearchResponse {
    hits: SearchHit[];
    total: number;
}

export type SearchHit = DatasourceHit | TableHit | ColumnHit | MetricHit;

export interface BaseHit {
    id: string;
    score: number;
    type: string;
    description?: string;
}

export interface DatasourceHit extends BaseHit {
    type: 'DATASOURCE';
    name: string;
    slug: string;
    engine: string;
}

export interface TableHit extends BaseHit {
    type: 'TABLE';
    name: string;
    physical_name: string;
    datasource_id: string;
    critical_rules: string[];
}

export interface ColumnHit extends BaseHit {
    type: 'COLUMN';
    name: string;
    semantic_name?: string;
    table_name: string;
    data_type: string;
}

export interface MetricHit extends BaseHit {
    type: 'METRIC';
    name: string;
    sql_template: string;
}

export interface GraphRequest {
    datasource_slug: string;
    anchor_entities: string[];
}

export interface GraphResponse {
    path_found: boolean;
    relationships: SchemaEdgeDTO[];
    bridge_tables: string[];
}

export interface SchemaEdgeDTO {
    source_table: string;
    source_column: string;
    target_table: string;
    target_column: string;
    relationship_type: string;
    join_condition: string;
}

export interface ValueValidationRequest {
    datasource_slug: string;
    target: { table: string; column: string };
    proposed_values: string[];
}

export interface ValueValidationResponse {
    valid: boolean;
    mappings: Record<string, string>;
    unresolved: string[];
}
