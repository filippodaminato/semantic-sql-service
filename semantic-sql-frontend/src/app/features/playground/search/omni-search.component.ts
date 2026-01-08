import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatSelectModule } from '@angular/material/select';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { RetrievalService } from '../../../core/services/retrieval.service';
import { SearchResponse } from '../../../core/models/retrieval.models';

@Component({
    selector: 'app-omni-search',
    standalone: true,
    imports: [
        CommonModule,
        FormsModule,
        MatInputModule,
        MatButtonModule,
        MatIconModule,
        MatSelectModule,
        MatProgressSpinnerModule
    ],
    templateUrl: './omni-search.component.html'
})
export class OmniSearchComponent {
    query = '';
    datasourceSlug = '';
    selectedEntityTypes: any[] = [];
    results: SearchResponse | null = null;
    loading = false;

    constructor(private retrievalService: RetrievalService) { }

    search() {
        if (!this.query.trim()) return;

        this.loading = true;
        this.retrievalService.search({
            query: this.query,
            filters: {
                datasource_slug: this.datasourceSlug || undefined,
                entity_types: this.selectedEntityTypes.length ? this.selectedEntityTypes : undefined
            }
        }).subscribe({
            next: (res) => {
                this.results = res;
                this.loading = false;
            },
            error: (err) => {
                console.error(err);
                this.loading = false;
                // TODO: Toast error
            }
        });
    }

    getScoreColor(score: number): string {
        if (score >= 0.8) return 'text-green-600';
        if (score >= 0.5) return 'text-yellow-600';
        return 'text-gray-400';
    }
}
