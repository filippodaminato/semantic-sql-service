import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import {
    SearchRequest, SearchResponse,
    GraphRequest, GraphResponse,
    ValueValidationRequest, ValueValidationResponse
} from '../models/retrieval.models';

@Injectable({
    providedIn: 'root'
})
export class RetrievalService {
    private apiUrl = 'http://localhost:8000/api/v1/retrieval';

    constructor(private http: HttpClient) { }

    search(req: SearchRequest): Observable<SearchResponse> {
        return this.http.post<SearchResponse>(`${this.apiUrl}/search`, req);
    }

    expandGraph(req: GraphRequest): Observable<GraphResponse> {
        return this.http.post<GraphResponse>(`${this.apiUrl}/graph/expand`, req);
    }

    validateValues(req: ValueValidationRequest): Observable<ValueValidationResponse> {
        return this.http.post<ValueValidationResponse>(`${this.apiUrl}/values/validate`, req);
    }

    explainConcepts(concepts: string[], datasourceSlug: string): Observable<any> {
        return this.http.post(`${this.apiUrl}/concepts/explain`, { concepts, datasource_slug: datasourceSlug });
    }

    searchGoldenSql(query: string, datasourceSlug: string): Observable<any> {
        return this.http.post(`${this.apiUrl}/golden-sql/search`, { query, datasource_slug: datasourceSlug });
    }
}
