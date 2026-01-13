import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import {
    Datasource, TableNode, ColumnNode, SchemaEdge, SemanticMetric, SemanticSynonym,
    ContextRule, NominalValue, GoldenSQL, AmbiguityLog, GenerationTrace,
    OmniSearchResponse, GraphExpandResponse, MetricValidationResponse,
    GraphVisualizationResponse, GraphNode, GraphEdge, DatasourceUpdate
} from '../models/models';

@Injectable({
    providedIn: 'root'
})
export class OntologyService {
    private apiUrl = '/api/v1/ontology';

    constructor(private http: HttpClient) { }

    // Datasources
    getDatasources(): Observable<Datasource[]> {
        return this.http.get<Datasource[]>(`${this.apiUrl}/datasources`);
    }

    createDatasource(data: Partial<Datasource>): Observable<Datasource> {
        return this.http.post<Datasource>(`${this.apiUrl}/datasources`, data);
    }

    updateDatasource(id: string, data: Partial<Datasource>): Observable<Datasource> {
        return this.http.put<Datasource>(`${this.apiUrl}/datasources/${id}`, data);
    }

    deleteDatasource(id: string): Observable<void> {
        return this.http.delete<void>(`${this.apiUrl}/datasources/${id}`);
    }

    // Tables
    getTables(): Observable<TableNode[]> {
        return this.http.get<TableNode[]>(`${this.apiUrl}/tables`);
    }

    createTable(data: Partial<TableNode>): Observable<TableNode> {
        return this.http.post<TableNode>(`${this.apiUrl}/tables`, data);
    }

    updateTable(id: string, data: Partial<TableNode>): Observable<TableNode> {
        return this.http.put<TableNode>(`${this.apiUrl}/tables/${id}`, data);
    }

    deleteTable(id: string): Observable<void> {
        return this.http.delete<void>(`${this.apiUrl}/tables/${id}`);
    }

    // Columns
    updateColumn(id: string, data: Partial<ColumnNode>): Observable<ColumnNode> {
        return this.http.patch<ColumnNode>(`${this.apiUrl}/columns/${id}`, data);
    }

    // Relationships
    getRelationships(): Observable<SchemaEdge[]> {
        return this.http.get<SchemaEdge[]>(`${this.apiUrl}/relationships`);
    }

    createRelationship(data: Partial<SchemaEdge>): Observable<SchemaEdge> {
        return this.http.post<SchemaEdge>(`${this.apiUrl}/relationships`, data);
    }

    deleteRelationship(id: string): Observable<void> {
        return this.http.delete<void>(`${this.apiUrl}/relationships/${id}`);
    }
}

@Injectable({
    providedIn: 'root'
})
export class SemanticsService {
    private apiUrl = '/api/v1/semantics';

    constructor(private http: HttpClient) { }

    // Metrics
    getMetrics(): Observable<SemanticMetric[]> {
        return this.http.get<SemanticMetric[]>(`${this.apiUrl}/metrics`);
    }

    createMetric(data: Partial<SemanticMetric>): Observable<SemanticMetric> {
        return this.http.post<SemanticMetric>(`${this.apiUrl}/metrics`, data);
    }

    updateMetric(id: string, data: Partial<SemanticMetric>): Observable<SemanticMetric> {
        return this.http.put<SemanticMetric>(`${this.apiUrl}/metrics/${id}`, data);
    }

    deleteMetric(id: string): Observable<void> {
        return this.http.delete<void>(`${this.apiUrl}/metrics/${id}`);
    }

    // Synonyms
    getSynonyms(): Observable<SemanticSynonym[]> {
        return this.http.get<SemanticSynonym[]>(`${this.apiUrl}/synonyms`);
    }

    createSynonym(data: Partial<SemanticSynonym>): Observable<SemanticSynonym> {
        return this.http.post<SemanticSynonym>(`${this.apiUrl}/synonyms`, data);
    }

    deleteSynonym(id: string): Observable<void> {
        return this.http.delete<void>(`${this.apiUrl}/synonyms/${id}`);
    }
}

@Injectable({
    providedIn: 'root'
})
export class AdminService {
    private apiUrl = '/api/v1/admin';

    constructor(private http: HttpClient) { }

    // --- Datasources ---
    getDatasources(): Observable<Datasource[]> {
        return this.http.get<Datasource[]>(`${this.apiUrl}/datasources`);
    }

    createDatasource(data: Partial<Datasource>): Observable<Datasource> {
        return this.http.post<Datasource>(`${this.apiUrl}/datasources`, data);
    }

    getDatasource(id: string): Observable<Datasource> {
        return this.http.get<Datasource>(`${this.apiUrl}/datasources/${id}`);
    }

    updateDatasource(id: string, data: DatasourceUpdate): Observable<Datasource> {
        return this.http.put<Datasource>(`${this.apiUrl}/datasources/${id}`, data);
    }

    deleteDatasource(id: string): Observable<void> {
        return this.http.delete<void>(`${this.apiUrl}/datasources/${id}`);
    }

    refreshIndex(id: string): Observable<any> {
        return this.http.post(`${this.apiUrl}/datasources/${id}/refresh-index`, {});
    }

    getDatasourceTables(id: string): Observable<TableNode[]> {
        return this.http.get<TableNode[]>(`${this.apiUrl}/datasources/${id}/tables`);
    }

    // --- Tables ---
    createTable(data: Partial<TableNode>): Observable<TableNode> {
        return this.http.post<TableNode>(`${this.apiUrl}/tables`, data);
    }

    getTable(id: string): Observable<TableNode> {
        return this.http.get<TableNode>(`${this.apiUrl}/tables/${id}`);
    }

    updateTable(id: string, data: Partial<TableNode>): Observable<TableNode> {
        return this.http.put<TableNode>(`${this.apiUrl}/tables/${id}`, data);
    }

    deleteTable(id: string): Observable<void> {
        return this.http.delete<void>(`${this.apiUrl}/tables/${id}`);
    }

    getTableRelationships(id: string): Observable<{ incoming: SchemaEdge[], outgoing: SchemaEdge[] }> {
        return this.http.get<{ incoming: SchemaEdge[], outgoing: SchemaEdge[] }>(`${this.apiUrl}/tables/${id}/relationships`);
    }

    // --- Columns ---
    updateColumn(id: string, data: Partial<ColumnNode>): Observable<ColumnNode> {
        return this.http.put<ColumnNode>(`${this.apiUrl}/columns/${id}`, data);
    }

    getColumnRules(id: string): Observable<ContextRule[]> {
        return this.http.get<ContextRule[]>(`${this.apiUrl}/columns/${id}/rules`);
    }

    getColumnValues(id: string): Observable<NominalValue[]> {
        return this.http.get<NominalValue[]>(`${this.apiUrl}/columns/${id}/values`);
    }

    syncColumnValues(id: string): Observable<any> {
        return this.http.post(`${this.apiUrl}/columns/${id}/values/sync`, {});
    }

    addManualValue(id: string, value: string): Observable<NominalValue> {
        return this.http.post<NominalValue>(`${this.apiUrl}/columns/${id}/values/manual`, { value });
    }

    // --- Relationships ---
    createRelationship(data: Partial<SchemaEdge>): Observable<SchemaEdge> {
        return this.http.post<SchemaEdge>(`${this.apiUrl}/relationships`, data);
    }

    deleteRelationship(id: string): Observable<void> {
        return this.http.delete<void>(`${this.apiUrl}/relationships/${id}`);
    }

    // --- Metrics ---
    getMetrics(): Observable<SemanticMetric[]> {
        return this.http.get<SemanticMetric[]>(`${this.apiUrl}/metrics`);
    }

    createMetric(data: Partial<SemanticMetric>): Observable<SemanticMetric> {
        return this.http.post<SemanticMetric>(`${this.apiUrl}/metrics`, data);
    }

    updateMetric(id: string, data: Partial<SemanticMetric>): Observable<SemanticMetric> {
        return this.http.put<SemanticMetric>(`${this.apiUrl}/metrics/${id}`, data);
    }

    validateMetric(id: string): Observable<MetricValidationResponse> {
        return this.http.post<MetricValidationResponse>(`${this.apiUrl}/metrics/${id}/validate`, {});
    }

    // --- Synonyms ---
    getSynonyms(): Observable<SemanticSynonym[]> {
        return this.http.get<SemanticSynonym[]>(`${this.apiUrl}/synonyms`);
    }

    createSynonymBulk(synonyms: Partial<SemanticSynonym>[]): Observable<any> {
        return this.http.post(`${this.apiUrl}/synonyms/bulk`, synonyms);
    }

    deleteSynonym(id: string): Observable<void> {
        return this.http.delete<void>(`${this.apiUrl}/synonyms/${id}`);
    }

    // --- Context Rules ---
    createContextRule(data: Partial<ContextRule>): Observable<ContextRule> {
        return this.http.post<ContextRule>(`${this.apiUrl}/context-rules`, data);
    }

    deleteContextRule(id: string): Observable<void> {
        return this.http.delete<void>(`${this.apiUrl}/context-rules/${id}`);
    }

    // --- Golden SQL ---
    getGoldenSQL(): Observable<GoldenSQL[]> {
        return this.http.get<GoldenSQL[]>(`${this.apiUrl}/golden-sql`);
    }

    createGoldenSQL(data: Partial<GoldenSQL>): Observable<GoldenSQL> {
        return this.http.post<GoldenSQL>(`${this.apiUrl}/golden-sql`, data);
    }

    updateGoldenSQL(id: string, data: Partial<GoldenSQL>): Observable<GoldenSQL> {
        return this.http.put<GoldenSQL>(`${this.apiUrl}/golden-sql/${id}`, data);
    }

    importGoldenSQL(pairs: Partial<GoldenSQL>[]): Observable<any> {
        return this.http.post(`${this.apiUrl}/golden-sql/import`, pairs);
    }

    // --- Visualization ---
    getGraphVisualization(
        datasourceId?: string,
        includeColumns: boolean = false,
        layout: string = 'horizontal'
    ): Observable<GraphVisualizationResponse> {
        let params: any = { layout, include_columns: includeColumns };
        if (datasourceId) {
            params.datasource_id = datasourceId;
        }
        return this.http.get<GraphVisualizationResponse>(
            `${this.apiUrl}/graph/visualize`,
            { params }
        );
    }
}

@Injectable({
    providedIn: 'root'
})
export class RetrievalService {
    private apiUrl = '/api/v1/retrieval';

    constructor(private http: HttpClient) { }

    search(query: string, limit: number = 5): Observable<OmniSearchResponse> {
        return this.http.post<OmniSearchResponse>(`${this.apiUrl}/search`, { query, limit });
    }

    expandGraph(nodeId: string): Observable<GraphExpandResponse> {
        return this.http.post<GraphExpandResponse>(`${this.apiUrl}/graph/expand`, { node_id: nodeId });
    }

    validateValues(values: string[]): Observable<any> {
        return this.http.post(`${this.apiUrl}/values/validate`, { values });
    }

    inspectSchema(context: string): Observable<any> {
        return this.http.post(`${this.apiUrl}/schema/inspect`, { context });
    }

    searchGoldenSQL(query: string): Observable<GoldenSQL[]> {
        return this.http.post<GoldenSQL[]>(`${this.apiUrl}/golden-sql/search`, { query });
    }

    explainConcepts(concepts: string[]): Observable<any> {
        return this.http.post(`${this.apiUrl}/concepts/explain`, { concepts });
    }

    globalEmbeddingSync(): Observable<any> {
        return this.http.post(`${this.apiUrl}/admin/sync-embeddings`, {});
    }
}

@Injectable({
    providedIn: 'root'
})
export class ContextService {
    private apiUrl = '/api/v1/context';

    constructor(private http: HttpClient) { }

    // Nominal Values
    getNominalValues(): Observable<NominalValue[]> {
        return this.http.get<NominalValue[]>(`${this.apiUrl}/nominal-values`);
    }

    createNominalValue(data: Partial<NominalValue>): Observable<NominalValue> {
        return this.http.post<NominalValue>(`${this.apiUrl}/nominal-values`, data);
    }

    updateNominalValue(id: string, data: Partial<NominalValue>): Observable<NominalValue> {
        return this.http.put<NominalValue>(`${this.apiUrl}/nominal-values/${id}`, data);
    }

    deleteNominalValue(id: string): Observable<void> {
        return this.http.delete<void>(`${this.apiUrl}/nominal-values/${id}`);
    }

    // Rules
    getRules(): Observable<ContextRule[]> {
        return this.http.get<ContextRule[]>(`${this.apiUrl}/rules`);
    }

    createRule(data: Partial<ContextRule>): Observable<ContextRule> {
        return this.http.post<ContextRule>(`${this.apiUrl}/rules`, data);
    }

    updateRule(id: string, data: Partial<ContextRule>): Observable<ContextRule> {
        return this.http.put<ContextRule>(`${this.apiUrl}/rules/${id}`, data);
    }

    deleteRule(id: string): Observable<void> {
        return this.http.delete<void>(`${this.apiUrl}/rules/${id}`);
    }
}

@Injectable({
    providedIn: 'root'
})
export class LearningService {
    private apiUrl = '/api/v1/learning';

    constructor(private http: HttpClient) { }

    // Golden SQL (Feedback Loop)
    getGoldenSQL(): Observable<GoldenSQL[]> {
        return this.http.get<GoldenSQL[]>(`${this.apiUrl}/golden-sql`);
    }

    updateGoldenSQL(id: string, data: Partial<GoldenSQL>): Observable<GoldenSQL> {
        return this.http.put<GoldenSQL>(`${this.apiUrl}/golden-sql/${id}`, data);
    }

    // Ambiguity Logs
    getAmbiguityLogs(): Observable<AmbiguityLog[]> {
        return this.http.get<AmbiguityLog[]>(`${this.apiUrl}/ambiguity-logs`);
    }

    updateAmbiguityLog(id: string, data: Partial<AmbiguityLog>): Observable<AmbiguityLog> {
        return this.http.put<AmbiguityLog>(`${this.apiUrl}/ambiguity-logs/${id}`, data);
    }

    deleteAmbiguityLog(id: string): Observable<void> {
        return this.http.delete<void>(`${this.apiUrl}/ambiguity-logs/${id}`);
    }

    // Generation Traces
    getGenerationTraces(): Observable<GenerationTrace[]> {
        return this.http.get<GenerationTrace[]>(`${this.apiUrl}/generation-traces`);
    }

    deleteGenerationTrace(id: string): Observable<void> {
        return this.http.delete<void>(`${this.apiUrl}/generation-traces/${id}`);
    }
}
