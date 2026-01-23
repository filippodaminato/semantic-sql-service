
import { Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatSelectModule } from '@angular/material/select';
import { MatIconModule } from '@angular/material/icon';
import { MatCardModule } from '@angular/material/card';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTooltipModule } from '@angular/material/tooltip';
import { DiscoveryService } from '../../../core/services/discovery.service';
import { JsonPipe } from '@angular/common';

@Component({
    selector: 'app-retrieval-playground',
    standalone: true,
    imports: [
        CommonModule,
        FormsModule,
        MatFormFieldModule,
        MatInputModule,
        MatButtonModule,
        MatSelectModule,
        MatIconModule,
        MatCardModule,
        MatProgressSpinnerModule,
        MatTooltipModule,
        JsonPipe
    ],
    template: `
    <div class="min-h-full w-full bg-[#0a0e14] relative overflow-hidden flex flex-col">

      <!-- Ambient Background Glow -->
      <div class="absolute top-0 left-0 w-full h-[500px] bg-gradient-to-b from-purple-900/10 via-transparent to-transparent pointer-events-none"></div>
      <div class="absolute top-[-20%] right-[-10%] w-[600px] h-[600px] bg-indigo-600/10 rounded-full blur-[120px] pointer-events-none"></div>

      <!-- Main Content -->
      <div class="flex-1 flex flex-col p-8 max-w-7xl mx-auto w-full relative z-10 space-y-8">

        <!-- Header -->
        <div class="flex items-center gap-4 border-b border-white/5 pb-6">
          <div class="p-3 bg-purple-500/10 rounded-xl border border-purple-500/20 shadow-[0_0_15px_rgba(168,85,247,0.1)]">
            <mat-icon class="text-purple-400 scale-125">science</mat-icon>
          </div>
          <div>
            <h1 class="text-3xl font-black text-white tracking-tight">Retrieval Playground</h1>
            <p class="text-gray-400 font-light mt-1">Test drive the Discovery API with live queries and instant feedback.</p>
          </div>
        </div>

        <!-- Two Column Layout -->
        <div class="grid grid-cols-1 lg:grid-cols-12 gap-8 h-full">

          <!-- Left Panel: Controls -->
          <div class="lg:col-span-4 space-y-6">
            <div class="bg-[#141a23] rounded-2xl border border-white/5 p-6 shadow-xl backdrop-blur-sm relative overflow-hidden group">
               <!-- Subtle gradient overlay on card -->
               <div class="absolute inset-0 bg-gradient-to-br from-white/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none"></div>

               <h2 class="text-lg font-bold text-white mb-6 flex items-center gap-2">
                 <mat-icon class="text-blue-400">tune</mat-icon> Configuration
               </h2>

               <div class="space-y-4 relative z-10">
                  <!-- Endpoint -->
                  <div class="space-y-1">
                    <label class="text-xs font-mono text-gray-500 uppercase tracking-wider ml-1">Endpoint</label>
                    <mat-form-field appearance="outline" class="w-full custom-dark-field">
                      <mat-select [(ngModel)]="selectedEndpoint" (selectionChange)="clearResults()" placeholder="Select endpoint">
                        <mat-option value="datasources">Datasources</mat-option>
                        <mat-option value="tables">Tables</mat-option>
                        <mat-option value="columns">Columns</mat-option>
                        <mat-option value="metrics">Metrics</mat-option>
                        <mat-option value="golden_sql">Golden SQL</mat-option>
                        <mat-option value="synonyms">Synonyms</mat-option>
                        <mat-option value="context_rules">Context Rules</mat-option>
                        <mat-option value="low_cardinality_values">Low Cardinality Values</mat-option>
                        <mat-option value="edges">Edges</mat-option>
                      </mat-select>
                      <mat-icon matPrefix class="text-gray-500 mr-2">api</mat-icon>
                    </mat-form-field>
                  </div>
                  
                  <!-- Query -->
                   <div class="space-y-1">
                    <label class="text-xs font-mono text-gray-500 uppercase tracking-wider ml-1">Search Query</label>
                    <mat-form-field appearance="outline" class="w-full custom-dark-field">
                      <input matInput [(ngModel)]="query" placeholder="e.g. revenue by region" (keydown.enter)="search()" autocomplete="off">
                      <mat-icon matSuffix class="text-gray-500">search</mat-icon>
                    </mat-form-field>
                  </div>

                  <!-- Response Mode -->
                  <div class="space-y-1">
                    <label class="text-xs font-mono text-gray-500 uppercase tracking-wider ml-1">Response Mode</label>
                    <mat-form-field appearance="outline" class="w-full custom-dark-field">
                      <mat-select [(ngModel)]="responseMode" (selectionChange)="clearResults()" placeholder="Select mode">
                        <mat-option value="json">Standard (JSON)</mat-option>
                        <mat-option value="mcp">MCP (Text)</mat-option>
                      </mat-select>
                      <mat-icon matPrefix class="text-gray-500 mr-2">code</mat-icon>
                    </mat-form-field>
                  </div>

                  <!-- Limit -->
                  <div class="space-y-1">
                     <label class="text-xs font-mono text-gray-500 uppercase tracking-wider ml-1">Limit</label>
                     <mat-form-field appearance="outline" class="w-full custom-dark-field">
                       <input matInput type="number" [(ngModel)]="limit" min="1" max="100" (change)="onLimitChange()">
                     </mat-form-field>
                  </div>
                  
                  <!-- Min Ratio -->
                  <div class="space-y-1">
                     <label class="text-xs font-mono text-gray-500 uppercase tracking-wider ml-1">Min Ratio (0-1)</label>
                     <mat-form-field appearance="outline" class="w-full custom-dark-field">
                       <input matInput type="number" [(ngModel)]="minRatioToBest" min="0" max="1" step="0.05" (change)="clearResults()">
                     </mat-form-field>
                  </div>

                  <!-- Page (only show if pagination is available) -->
                  <div class="space-y-1" *ngIf="hasSearched() && pagination()">
                     <label class="text-xs font-mono text-gray-500 uppercase tracking-wider ml-1">Page</label>
                     <mat-form-field appearance="outline" class="w-full custom-dark-field">
                       <input matInput type="number" [(ngModel)]="page" [min]="1" [max]="pagination()!.total_pages" (change)="goToPage(page())">
                     </mat-form-field>
                  </div>

                  <!-- Context Filters -->
                  <div class="pt-4 border-t border-white/5 space-y-4" *ngIf="selectedEndpoint() !== 'datasources'">
                      <div class="flex items-center gap-2 text-gray-400 mb-2">
                        <mat-icon class="text-xs scale-75">filter_list</mat-icon>
                        <span class="text-xs font-bold uppercase tracking-wider">Context Filters</span>
                      </div>

                      <mat-form-field appearance="outline" class="w-full custom-dark-field text-sm">
                          <mat-label>Datasource Slug</mat-label>
                          <input matInput [(ngModel)]="datasourceSlug" placeholder="e.g. sales-db">
                      </mat-form-field>

                      <mat-form-field appearance="outline" class="w-full custom-dark-field text-sm"
                          *ngIf="['columns', 'context_rules', 'low_cardinality_values', 'edges'].includes(selectedEndpoint())">
                          <mat-label>Table Slug</mat-label>
                          <input matInput [(ngModel)]="tableSlug" placeholder="e.g. orders">
                      </mat-form-field>

                      <mat-form-field appearance="outline" class="w-full custom-dark-field text-sm"
                          *ngIf="selectedEndpoint() === 'low_cardinality_values'">
                          <mat-label>Column Slug</mat-label>
                          <input matInput [(ngModel)]="columnSlug" placeholder="e.g. status">
                      </mat-form-field>
                  </div>

                  <div class="pt-6">
                    <button mat-flat-button color="primary" class="w-full !h-12 !rounded-xl !text-base shadow-[0_0_20px_rgba(59,130,246,0.4)] hover:shadow-[0_0_30px_rgba(59,130,246,0.6)] transition-all"
                        (click)="search()" [disabled]="loading()">
                        <mat-icon *ngIf="!loading()" class="mr-2">play_arrow</mat-icon>
                        <mat-progress-spinner *ngIf="loading()" mode="indeterminate" diameter="20" class="mr-2 inline-block"></mat-progress-spinner>
                        <span *ngIf="!loading()">EXECUTE SEARCH</span>
                        <span *ngIf="loading()">SEARCHING...</span>
                    </button>
                  </div>

               </div>
            </div>
            
             <!-- Documentation Hint Widget -->
             <div class="bg-blue-900/10 border border-blue-500/20 rounded-xl p-4 flex gap-3">
                <mat-icon class="text-blue-400 shrink-0">info</mat-icon>
                <div class="text-sm">
                    <p class="font-bold text-blue-200 mb-1">Did you know?</p>
                    <p class="text-blue-300_70 text-gray-400 leading-relaxed">
                        Discovery uses <strong>Hybrid Search</strong>, combining dense vector embeddings with sparse keyword matching (BM25) for optimal retrieval.
                    </p>
                </div>
            </div>
          </div>

          <!-- Right Panel: Results -->
          <div class="lg:col-span-8">
            <div class="bg-[#141a23] rounded-2xl border border-white/5 h-full min-h-[500px] flex flex-col shadow-xl overflow-hidden relative">
               
               <!-- Toolbar -->
               <div class="px-6 py-4 border-b border-white/5 flex justify-between items-center bg-[#0d1218]">
                  <div class="flex items-center gap-2">
                     <h2 class="text-lg font-bold text-white">Results</h2>
                     <span *ngIf="hasSearched()" class="bg-green-500/10 text-green-400 text-xs px-2 py-0.5 rounded border border-green-500/20 font-mono">
                        {{ resultTime() }}ms
                     </span>
                     <span *ngIf="hasSearched() && pagination()" class="bg-blue-500/10 text-blue-400 text-xs px-2 py-0.5 rounded border border-blue-500/20 font-mono">
                        {{ pagination()!.total }} total
                     </span>
                     <span *ngIf="hasSearched() && !pagination() && !mcpResult()" class="bg-blue-500/10 text-blue-400 text-xs px-2 py-0.5 rounded border border-blue-500/20 font-mono">
                        {{ results().length }} hits
                     </span>
                     <span *ngIf="mcpResult()" class="bg-purple-500/10 text-purple-400 text-xs px-2 py-0.5 rounded border border-purple-500/20 font-mono">
                        MCP TEXT
                     </span>
                  </div>
                  <div class="flex gap-2">
                     <button mat-icon-button class="!text-gray-500 hover:!text-white transition-colors" matTooltip="Copy Result" (click)="copyResults()">
                        <mat-icon class="text-sm">content_copy</mat-icon>
                     </button>
                     <button mat-icon-button class="!text-gray-500 hover:!text-white transition-colors" matTooltip="Clear" (click)="clearResults()">
                        <mat-icon class="text-sm">delete_outline</mat-icon>
                     </button>
                  </div>
               </div>

               <!-- Pagination Controls -->
               <div *ngIf="pagination() && pagination()!.total_pages > 1" class="px-6 py-3 border-b border-white/5 bg-[#0d1218] flex items-center justify-between">
                  <div class="flex items-center gap-2 text-sm text-gray-400">
                     <span>Page {{ pagination()!.page }} of {{ pagination()!.total_pages }}</span>
                     <span class="text-gray-600">•</span>
                     <span>{{ pagination()!.total }} total results</span>
                     <span class="text-gray-600">•</span>
                     <span>{{ pagination()!.limit }} per page</span>
                  </div>
                  <div class="flex items-center gap-2">
                     <button mat-icon-button 
                        [disabled]="!pagination()!.has_prev" 
                        (click)="prevPage()"
                        class="!text-gray-500 hover:!text-white disabled:!opacity-30 disabled:!cursor-not-allowed transition-colors"
                        matTooltip="Previous page">
                        <mat-icon>chevron_left</mat-icon>
                     </button>
                     <span class="text-sm text-gray-400 px-3 font-mono">{{ pagination()!.page }} / {{ pagination()!.total_pages }}</span>
                     <button mat-icon-button 
                        [disabled]="!pagination()!.has_next" 
                        (click)="nextPage()"
                        class="!text-gray-500 hover:!text-white disabled:!opacity-30 disabled:!cursor-not-allowed transition-colors"
                        matTooltip="Next page">
                        <mat-icon>chevron_right</mat-icon>
                     </button>
                  </div>
               </div>

               <!-- Content Area -->
               <div class="flex-1 relative overflow-auto custom-scrollbar bg-[#0d1218]">
                   <!-- Loading State -->
                   <div *ngIf="loading()" class="absolute inset-0 z-20 flex flex-col items-center justify-center bg-[#0d1218]/80 backdrop-blur-sm">
                       <mat-progress-spinner mode="indeterminate" diameter="50" color="accent"></mat-progress-spinner>
                       <p class="mt-4 text-blue-400 font-mono text-sm animate-pulse">Processing query...</p>
                   </div>
                   
                   <!-- Empty State (Intro) -->
                   <div *ngIf="!hasSearched() && !loading()" class="h-full flex flex-col items-center justify-center text-center p-12 opacity-50">
                       <div class="p-6 bg-white/5 rounded-full mb-6 animate-float">
                          <mat-icon class="text-5xl text-gray-600 scale-150">troubleshoot</mat-icon>
                       </div>
                       <h3 class="text-xl font-bold text-gray-300">Ready to Discover</h3>
                       <p class="text-gray-500 max-w-sm mt-2">Select an endpoint and enter a query to inspect your semantic graph.</p>
                   </div>

                   <!-- Empty State (No Results) -->
                   <div *ngIf="hasSearched() && results().length === 0 && !mcpResult() && !loading()" class="h-full flex flex-col items-center justify-center text-center p-12">
                       <mat-icon class="text-5xl text-gray-700 mb-4">search_off</mat-icon>
                       <h3 class="text-lg font-bold text-gray-400">No results found</h3>
                       <p class="text-gray-600 mt-2">Try adjusting your query or filters.</p>
                   </div>

                   <!-- JSON View -->
                   <div *ngIf="hasSearched() && results().length > 0 && !mcpResult()" class="p-6">
                       <pre class="font-mono text-sm text-blue-300 leading-relaxed bg-[#0a0e14] p-6 rounded-xl border border-white/5 shadow-inner overflow-x-auto selection:bg-blue-500/30 selection:text-white">{{ results() | json }}</pre>
                   </div>

                   <!-- MCP Text View -->
                   <div *ngIf="hasSearched() && mcpResult()" class="p-6">
                       <pre class="font-mono text-sm text-purple-300 leading-relaxed bg-[#0a0e14] p-6 rounded-xl border border-purple-500/10 shadow-inner overflow-x-auto whitespace-pre-wrap selection:bg-purple-500/30 selection:text-white">{{ mcpResult() }}</pre>
                   </div>

                   <!-- Error -->
                   <div *ngIf="error()" class="m-6 p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-200 flex gap-3 items-start">
                       <mat-icon class="text-red-400 shrink-0">error_outline</mat-icon>
                       <div>
                           <p class="font-bold text-red-400 text-sm">Error Occurred</p>
                           <p class="text-xs opacity-80 mt-1 font-mono">{{ error() }}</p>
                       </div>
                   </div>
               </div>
            </div>
          </div>

        </div>
      </div>
    </div>
  `,
    styles: [`
    /* Custom Scrollbar for the dark theme */
    .custom-scrollbar::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }
    .custom-scrollbar::-webkit-scrollbar-track {
        background: #0d1218; 
    }
    .custom-scrollbar::-webkit-scrollbar-thumb {
        background: #2d3748; 
        border-radius: 4px;
    }
    .custom-scrollbar::-webkit-scrollbar-thumb:hover {
        background: #4a5568; 
    }

    /* Input Field Overrides for Dark Mode integration */
    ::ng-deep .custom-dark-field .mat-mdc-text-field-wrapper {
        background-color: #0d1218 !important;   /* Darker background for inputs */
        border-radius: 8px !important;
        border: 1px solid rgba(255, 255, 255, 0.05);
    }
    ::ng-deep .custom-dark-field .mat-mdc-form-field-icon-prefix > .mat-icon,
    ::ng-deep .custom-dark-field .mat-mdc-form-field-icon-suffix > .mat-icon {
        color: #718096 !important;
    }
    ::ng-deep .custom-dark-field .mat-mdc-input-element {
        color: #e2e8f0 !important;
        caret-color: #60a5fa !important;
    }
    ::ng-deep .custom-dark-field .mat-mdc-input-element::placeholder {
        color: #4a5568 !important;
    }
    ::ng-deep .custom-dark-field .mat-mdc-form-field-focus-overlay {
        opacity: 0 !important; /* Remove default focus overlay */
    }
    ::ng-deep .custom-dark-field.mat-focused .mat-mdc-text-field-wrapper {
        border-color: rgba(96, 165, 250, 0.5) !important; /* Blue border on focus */
    }
    ::ng-deep .custom-dark-field .mat-mdc-floating-label {
        color: #718096 !important;
    }
    ::ng-deep .custom-dark-field.mat-focused .mat-mdc-floating-label {
        color: #60a5fa !important;
    }

    /* Select Panel Override */
    ::ng-deep .mat-mdc-select-panel {
        background-color: #1a202c !important;
    }
    ::ng-deep .mat-mdc-option {
        color: #e2e8f0 !important;
    }
    ::ng-deep .mat-mdc-option:hover, ::ng-deep .mat-mdc-option:focus {
        background-color: rgba(255, 255, 255, 0.05) !important;
    }
    ::ng-deep .mat-mdc-option.mdc-list-item--selected {
        background-color: rgba(96, 165, 250, 0.1) !important;
        color: #60a5fa !important;
    }
    
    .animate-float {
        animation: float 6s ease-in-out infinite;
    }

    @keyframes float {
        0% { transform: translateY(0px); }
        50% { transform: translateY(-10px); }
        100% { transform: translateY(0px); }
    }
  `]
})
export class RetrievalPlaygroundComponent {
    private discoveryService = inject(DiscoveryService);

    selectedEndpoint = signal<string>('tables');
    responseMode = signal<string>('json');
    query = signal<string>('');
    datasourceSlug = signal<string>('');
    tableSlug = signal<string>('');
    columnSlug = signal<string>('');
    limit = signal<number>(10);
    minRatioToBest = signal<number | undefined>(undefined);
    page = signal<number>(1);

    results = signal<any[]>([]);
    mcpResult = signal<string | null>(null);
    pagination = signal<{ total: number; page: number; limit: number; has_next: boolean; has_prev: boolean; total_pages: number } | null>(null);
    loading = signal<boolean>(false);
    error = signal<string | null>(null);
    hasSearched = signal<boolean>(false);
    resultTime = signal<number | null>(null);

    clearResults() {
        this.results.set([]);
        this.mcpResult.set(null);
        this.pagination.set(null);
        this.error.set(null);
        this.hasSearched.set(false);
        this.page.set(1);
    }

    copyResults() {
        if (this.responseMode() === 'mcp' && this.mcpResult()) {
            navigator.clipboard.writeText(this.mcpResult()!);
        } else if (this.results().length > 0) {
            navigator.clipboard.writeText(JSON.stringify(this.results(), null, 2));
        }
    }

    search() {
        this.loading.set(true);
        this.error.set(null);
        this.mcpResult.set(null); // clear previous
        this.results.set([]);

        const start = performance.now();

        const ep = this.selectedEndpoint();
        const isMcp = this.responseMode() === 'mcp';

        const baseReq = {
            query: this.query(),
            page: this.page(),
            limit: this.limit(),
            mcp: isMcp,
            min_ratio_to_best: this.minRatioToBest()
        };

        let obs;

        switch (ep) {
            case 'datasources':
                obs = this.discoveryService.searchDatasources(baseReq);
                break;
            case 'tables':
                obs = this.discoveryService.searchTables({ ...baseReq, datasource_slug: this.datasourceSlug() });
                break;
            case 'columns':
                obs = this.discoveryService.searchColumns({ ...baseReq, datasource_slug: this.datasourceSlug(), table_slug: this.tableSlug() });
                break;
            case 'metrics':
                obs = this.discoveryService.searchMetrics({ ...baseReq, datasource_slug: this.datasourceSlug() });
                break;
            case 'golden_sql':
                obs = this.discoveryService.searchGoldenSql({ ...baseReq, datasource_slug: this.datasourceSlug() });
                break;
            case 'synonyms':
                obs = this.discoveryService.searchSynonyms({ ...baseReq, datasource_slug: this.datasourceSlug() });
                break;
            case 'context_rules':
                obs = this.discoveryService.searchContextRules({ ...baseReq, datasource_slug: this.datasourceSlug(), table_slug: this.tableSlug() });
                break;
            case 'low_cardinality_values':
                obs = this.discoveryService.searchLowCardinalityValues({ ...baseReq, datasource_slug: this.datasourceSlug(), table_slug: this.tableSlug(), column_slug: this.columnSlug() });
                break;
            case 'edges':
                obs = this.discoveryService.searchEdges({ ...baseReq, datasource_slug: this.datasourceSlug(), table_slug: this.tableSlug() });
                break;
            default:
                this.error.set("Unknown endpoint");
                this.loading.set(false);
                return;
        }

        obs.subscribe({
            next: (data) => {
                // MCP Response
                if (data && 'res' in data) {
                    this.mcpResult.set(data.res);
                    // Clear pagination for MCP as it's embedded in text
                    this.pagination.set(null);
                }
                // Standard Paginated Response
                else if (data && 'items' in data) {
                    this.results.set(data.items);
                    this.pagination.set({
                        total: data.total,
                        page: data.page,
                        limit: data.limit,
                        has_next: data.has_next,
                        has_prev: data.has_prev,
                        total_pages: data.total_pages
                    });
                } else {
                    // Fallback
                    this.results.set(Array.isArray(data) ? data : []);
                    this.pagination.set(null);
                }
                this.resultTime.set(Math.round(performance.now() - start));
                this.hasSearched.set(true);
                this.loading.set(false);
            },
            error: (err) => {
                console.error(err);
                this.error.set(err.message || 'Error executing search');
                this.loading.set(false);
            }
        });
    }

    nextPage() {
        if (this.pagination()?.has_next) {
            this.page.set(this.page() + 1);
            this.search();
        }
    }

    prevPage() {
        if (this.pagination()?.has_prev) {
            this.page.set(this.page() - 1);
            this.search();
        }
    }

    goToPage(pageNum: number) {
        const pag = this.pagination();
        if (pag && pageNum >= 1 && pageNum <= pag.total_pages) {
            this.page.set(pageNum);
            this.search();
        }
    }

    onLimitChange() {
        // Reset to page 1 when limit changes
        this.page.set(1);
        // Optionally auto-search when limit changes
        if (this.hasSearched()) {
            this.search();
        }
    }
}

