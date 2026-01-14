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

    searchDatasources(req: DatasourceSearchRequest): Observable<PaginatedResponse<any>> {
        return this.http.post<PaginatedResponse<any>>(`${this.apiUrl}/datasources`, req);
    }

    searchTables(req: TableSearchRequest): Observable<PaginatedResponse<any>> {
        return this.http.post<PaginatedResponse<any>>(`${this.apiUrl}/tables`, req);
    }

    searchColumns(req: ColumnSearchRequest): Observable<PaginatedResponse<any>> {
        return this.http.post<PaginatedResponse<any>>(`${this.apiUrl}/columns`, req);
    }

    searchMetrics(req: MetricSearchRequest): Observable<PaginatedResponse<any>> {
        return this.http.post<PaginatedResponse<any>>(`${this.apiUrl}/metrics`, req);
    }

    searchGoldenSql(req: GoldenSQLSearchRequest): Observable<PaginatedResponse<any>> {
        return this.http.post<PaginatedResponse<any>>(`${this.apiUrl}/golden_sql`, req);
    }

    searchSynonyms(req: SynonymSearchRequest): Observable<PaginatedResponse<any>> {
        return this.http.post<PaginatedResponse<any>>(`${this.apiUrl}/synonyms`, req);
    }

    searchContextRules(req: ContextRuleSearchRequest): Observable<PaginatedResponse<any>> {
        return this.http.post<PaginatedResponse<any>>(`${this.apiUrl}/context_rules`, req);
    }

    searchLowCardinalityValues(req: LowCardinalityValueSearchRequest): Observable<PaginatedResponse<any>> {
        return this.http.post<PaginatedResponse<any>>(`${this.apiUrl}/low_cardinality_values`, req);
    }


    searchEdges(req: EdgeSearchRequest): Observable<PaginatedResponse<any>> {
        return this.http.post<PaginatedResponse<any>>(`${this.apiUrl}/edges`, req);
    }

    searchPaths(req: GraphPathRequest): Observable<GraphPathResult> {
        return this.http.post<GraphPathResult>(`${this.apiUrl}/paths`, req);
    }
}
