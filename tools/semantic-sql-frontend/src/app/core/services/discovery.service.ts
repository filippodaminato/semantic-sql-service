import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

// Paginated Response Interface
export interface PaginatedResponse<T> {
    items: T[];
    total: number;
    page: number;
    limit: number;
    has_next: boolean;
    has_prev: boolean;
    total_pages: number;
}

export interface DiscoverySearchRequest {
    query: string;
    page?: number;
    limit?: number;
    mcp?: boolean;
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

export interface GraphPathRequest {
    source_table_slug: string;
    target_table_slug: string;
    datasource_slug?: string;
    max_depth?: number;
}

export interface GraphPathResult {
    source_table: string;
    target_table: string;
    paths: any[];
    total_paths: number;
}

@Injectable({
    providedIn: 'root'
})
export class DiscoveryService {
    private apiUrl = 'http://localhost:8000/api/v1/discovery';

    constructor(private http: HttpClient) { }

    private getUrl(endpoint: string, mcp?: boolean): string {
        return mcp ? `${this.apiUrl}/mcp/${endpoint}` : `${this.apiUrl}/${endpoint}`;
    }

    searchDatasources(req: DatasourceSearchRequest): Observable<any> {
        return this.http.post<any>(this.getUrl('datasources', req.mcp), req);
    }

    searchTables(req: TableSearchRequest): Observable<any> {
        return this.http.post<any>(this.getUrl('tables', req.mcp), req);
    }

    searchColumns(req: ColumnSearchRequest): Observable<any> {
        return this.http.post<any>(this.getUrl('columns', req.mcp), req);
    }

    searchMetrics(req: MetricSearchRequest): Observable<any> {
        return this.http.post<any>(this.getUrl('metrics', req.mcp), req);
    }

    searchGoldenSql(req: GoldenSQLSearchRequest): Observable<any> {
        return this.http.post<any>(this.getUrl('golden_sql', req.mcp), req);
    }

    searchSynonyms(req: SynonymSearchRequest): Observable<any> {
        return this.http.post<any>(this.getUrl('synonyms', req.mcp), req);
    }

    searchContextRules(req: ContextRuleSearchRequest): Observable<any> {
        return this.http.post<any>(this.getUrl('context_rules', req.mcp), req);
    }

    searchLowCardinalityValues(req: LowCardinalityValueSearchRequest): Observable<any> {
        return this.http.post<any>(this.getUrl('low_cardinality_values', req.mcp), req);
    }


    searchEdges(req: EdgeSearchRequest): Observable<any> {
        return this.http.post<any>(this.getUrl('edges', req.mcp), req);
    }

    searchPaths(req: GraphPathRequest): Observable<GraphPathResult> {
        return this.http.post<GraphPathResult>(`${this.apiUrl}/paths`, req);
    }
}
