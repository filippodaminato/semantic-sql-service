import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface DiscoverySearchRequest {
    query: string;
    limit?: number;
}

export interface DatasourceSearchRequest extends DiscoverySearchRequest { }
export interface TableSearchRequest extends DiscoverySearchRequest {
    datasource_slug?: string;
}
export interface ColumnSearchRequest extends DiscoverySearchRequest {
    datasource_slug?: string;
    table_slug?: string;
}
export interface MetricSearchRequest extends DiscoverySearchRequest {
    datasource_slug?: string;
}
export interface GoldenSQLSearchRequest extends DiscoverySearchRequest {
    datasource_slug?: string;
}
export interface SynonymSearchRequest extends DiscoverySearchRequest {
    datasource_slug?: string;
}
export interface ContextRuleSearchRequest extends DiscoverySearchRequest {
    datasource_slug?: string;
    table_slug?: string;
}
export interface LowCardinalityValueSearchRequest extends DiscoverySearchRequest {
    datasource_slug?: string;
    table_slug?: string;
    column_slug?: string;
}
export interface EdgeSearchRequest extends DiscoverySearchRequest {
    datasource_slug?: string;
    table_slug?: string;
}

@Injectable({
    providedIn: 'root'
})
export class DiscoveryService {
    private apiUrl = 'http://localhost:8000/api/v1/discovery';

    constructor(private http: HttpClient) { }

    searchDatasources(req: DatasourceSearchRequest): Observable<any[]> {
        return this.http.post<any[]>(`${this.apiUrl}/datasources`, req);
    }

    searchTables(req: TableSearchRequest): Observable<any[]> {
        return this.http.post<any[]>(`${this.apiUrl}/tables`, req);
    }

    searchColumns(req: ColumnSearchRequest): Observable<any[]> {
        return this.http.post<any[]>(`${this.apiUrl}/columns`, req);
    }

    searchMetrics(req: MetricSearchRequest): Observable<any[]> {
        return this.http.post<any[]>(`${this.apiUrl}/metrics`, req);
    }

    searchGoldenSql(req: GoldenSQLSearchRequest): Observable<any[]> {
        return this.http.post<any[]>(`${this.apiUrl}/golden_sql`, req);
    }

    searchSynonyms(req: SynonymSearchRequest): Observable<any[]> {
        return this.http.post<any[]>(`${this.apiUrl}/synonyms`, req);
    }

    searchContextRules(req: ContextRuleSearchRequest): Observable<any[]> {
        return this.http.post<any[]>(`${this.apiUrl}/context_rules`, req);
    }

    searchLowCardinalityValues(req: LowCardinalityValueSearchRequest): Observable<any[]> {
        return this.http.post<any[]>(`${this.apiUrl}/low_cardinality_values`, req);
    }

    searchEdges(req: EdgeSearchRequest): Observable<any[]> {
        return this.http.post<any[]>(`${this.apiUrl}/edges`, req);
    }
}
