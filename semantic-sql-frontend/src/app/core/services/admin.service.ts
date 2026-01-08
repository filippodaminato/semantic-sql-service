import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import {
    Datasource, DatasourceCreate, RefreshIndexResponse,
    Table, TableCreate,
    Relationship,
    Metric,
    Synonym,
    ContextRule,
    NominalValue,
    GoldenSQL,
    GoldenSQLCreate
} from '../models/admin.models';

@Injectable({
    providedIn: 'root'
})
export class AdminService {
    private apiUrl = 'http://localhost:8000/api/v1/admin'; // TODO: Move to environment

    constructor(private http: HttpClient) { }

    // Datasources
    getDatasources(): Observable<Datasource[]> {
        return this.http.get<Datasource[]>(`${this.apiUrl}/datasources`);
    }

    getDatasource(id: string): Observable<Datasource> {
        return this.http.get<Datasource>(`${this.apiUrl}/datasources/${id}`);
    }

    createDatasource(data: DatasourceCreate): Observable<Datasource> {
        return this.http.post<Datasource>(`${this.apiUrl}/datasources`, data);
    }

    deleteDatasource(id: string): Observable<void> {
        return this.http.delete<void>(`${this.apiUrl}/datasources/${id}`);
    }

    refreshDatasourceIndex(id: string): Observable<RefreshIndexResponse> {
        return this.http.post<RefreshIndexResponse>(`${this.apiUrl}/datasources/${id}/refresh-index`, {});
    }

    updateDatasource(id: string, data: Partial<DatasourceCreate>): Observable<Datasource> {
        return this.http.put<Datasource>(`${this.apiUrl}/datasources/${id}`, data);
    }

    // Tables
    getTables(datasourceId: string): Observable<Table[]> {
        return this.http.get<Table[]>(`${this.apiUrl}/datasources/${datasourceId}/tables`);
    }

    getTable(id: string): Observable<Table> {
        return this.http.get<Table>(`${this.apiUrl}/tables/${id}/full`);
    }

    createTable(data: TableCreate): Observable<Table> {
        return this.http.post<Table>(`${this.apiUrl}/tables`, data);
    }

    updateTable(id: string, data: any): Observable<any> {
        return this.http.put(`${this.apiUrl}/tables/${id}`, data);
    }

    deleteTable(id: string): Observable<void> {
        return this.http.delete<void>(`${this.apiUrl}/tables/${id}`);
    }

    updateColumn(id: string, data: any): Observable<any> {
        return this.http.put(`${this.apiUrl}/columns/${id}`, data);
    }

    createColumn(tableId: string, data: any): Observable<any> {
        return this.http.post(`${this.apiUrl}/tables/${tableId}/columns`, data);
    }

    deleteColumn(columnId: string): Observable<any> {
        return this.http.delete(`${this.apiUrl}/columns/${columnId}`);
    }

    getGraph(datasourceId: string): Observable<any> {
        return this.http.get(`${this.apiUrl}/graph/visualize`, {
            params: { datasource_id: datasourceId }
        });
    }

    // Relationships
    getRelationships(tableId: string): Observable<any> {
        return this.http.get(`${this.apiUrl}/tables/${tableId}/relationships`);
    }

    getDatasourceRelationships(datasourceId: string): Observable<Relationship[]> {
        return this.http.get<Relationship[]>(`${this.apiUrl}/datasources/${datasourceId}/relationships`);
    }

    createRelationship(data: any): Observable<any> {
        return this.http.post(`${this.apiUrl}/relationships`, data);
    }

    deleteRelationship(id: string): Observable<void> {
        return this.http.delete<void>(`${this.apiUrl}/relationships/${id}`);
    }

    updateRelationship(id: string, data: any): Observable<any> {
        return this.http.put(`${this.apiUrl}/relationships/${id}`, data);
    }

    // Metrics
    getMetrics(datasourceId?: string): Observable<Metric[]> {
        let url = `${this.apiUrl}/metrics`;
        if (datasourceId) {
            url += `?datasource_id=${datasourceId}`;
        }
        return this.http.get<Metric[]>(url);
    }

    createMetric(data: any): Observable<Metric> {
        return this.http.post<Metric>(`${this.apiUrl}/metrics`, data);
    }

    updateMetric(id: string, data: any): Observable<any> {
        return this.http.put(`${this.apiUrl}/metrics/${id}`, data);
    }

    deleteMetric(id: string): Observable<void> {
        return this.http.delete<void>(`${this.apiUrl}/metrics/${id}`);
    }

    validateMetric(id: string): Observable<any> {
        return this.http.post(`${this.apiUrl}/metrics/${id}/validate`, {});
    }

    // Synonyms
    getSynonyms(): Observable<Synonym[]> {
        return this.http.get<Synonym[]>(`${this.apiUrl}/synonyms`);
    }

    createSynonymsBulk(data: any): Observable<any> {
        return this.http.post(`${this.apiUrl}/synonyms/bulk`, data);
    }

    deleteSynonym(id: string): Observable<void> {
        return this.http.delete<void>(`${this.apiUrl}/synonyms/${id}`);
    }

    updateSynonym(id: string, data: any): Observable<any> {
        return this.http.put(`${this.apiUrl}/synonyms/${id}`, data);
    }

    // Context Rules
    createContextRule(data: any): Observable<any> {
        return this.http.post(`${this.apiUrl}/context-rules`, data);
    }

    getColumnRules(columnId: string): Observable<ContextRule[]> {
        return this.http.get<ContextRule[]>(`${this.apiUrl}/columns/${columnId}/rules`);
    }

    deleteContextRule(id: string): Observable<void> {
        return this.http.delete<void>(`${this.apiUrl}/context-rules/${id}`);
    }

    // Nominal Values
    getColumnValues(columnId: string): Observable<NominalValue[]> {
        return this.http.get<NominalValue[]>(`${this.apiUrl}/columns/${columnId}/values`);
    }

    addManualValue(columnId: string, data: any): Observable<any> {
        return this.http.post(`${this.apiUrl}/columns/${columnId}/values/manual`, data);
    }

    deleteValue(id: string): Observable<void> {
        return this.http.delete<void>(`${this.apiUrl}/values/${id}`);
    }

    // Golden SQL
    getGoldenSQL(datasourceId?: string): Observable<GoldenSQL[]> {
        let url = `${this.apiUrl}/golden-sql`;
        if (datasourceId) {
            url += `?datasource_id=${datasourceId}`;
        }
        return this.http.get<GoldenSQL[]>(url);
    }

    createGoldenSQL(data: GoldenSQLCreate): Observable<GoldenSQL> {
        return this.http.post<GoldenSQL>(`${this.apiUrl}/golden-sql`, data);
    }

    updateGoldenSQL(id: string, data: Partial<GoldenSQLCreate>): Observable<any> {
        return this.http.put(`${this.apiUrl}/golden-sql/${id}`, data);
    }

    deleteGoldenSQL(id: string): Observable<void> {
        return this.http.delete<void>(`${this.apiUrl}/golden-sql/${id}`);
    }

    // Graph
    getGraphVisualization(datasourceId?: string): Observable<any> {
        let url = `${this.apiUrl}/graph/visualize`;
        if (datasourceId) url += `?datasource_id=${datasourceId}`;
        return this.http.get(url);
    }
}
