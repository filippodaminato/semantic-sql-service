
import { Component, inject, signal } from '@angular/core';
import { CommonModule, JsonPipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatSelectModule } from '@angular/material/select';
import { MatIconModule } from '@angular/material/icon';
import { MatCardModule } from '@angular/material/card';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTooltipModule } from '@angular/material/tooltip';
import { DiscoveryService, ContextSearchItem, ContextSearchEntity, ContextResolutionResponse } from '../../../core/services/discovery.service';

@Component({
    selector: 'app-resolve-context-playground',
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
      <div class="absolute top-0 left-0 w-full h-[500px] bg-gradient-to-b from-blue-900/10 via-transparent to-transparent pointer-events-none"></div>
      <div class="absolute top-[-20%] left-[-10%] w-[600px] h-[600px] bg-cyan-600/10 rounded-full blur-[120px] pointer-events-none"></div>

      <!-- Main Content -->
      <div class="flex-1 flex flex-col p-8 max-w-7xl mx-auto w-full relative z-10 space-y-8">

        <!-- Header -->
        <div class="flex items-center gap-4 border-b border-white/5 pb-6">
          <div class="p-3 bg-cyan-500/10 rounded-xl border border-cyan-500/20 shadow-[0_0_15px_rgba(34,211,238,0.1)]">
            <mat-icon class="text-cyan-400 scale-125">hub</mat-icon>
          </div>
          <div>
            <h1 class="text-3xl font-black text-white tracking-tight">Context Resolver</h1>
            <p class="text-gray-400 font-light mt-1">Unified Context Resolution: Scatter-Gather Search & Hierarchical Inference.</p>
          </div>
        </div>

        <!-- Two Column Layout -->
        <div class="grid grid-cols-1 lg:grid-cols-12 gap-8 h-full">

          <!-- Left Panel: Input Items -->
          <div class="lg:col-span-5 space-y-6">
            <div class="bg-[#141a23] rounded-2xl border border-white/5 p-6 shadow-xl backdrop-blur-sm relative overflow-hidden group min-h-[400px]">
               <!-- Subtle gradient overlay on card -->
               <div class="absolute inset-0 bg-gradient-to-br from-white/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none"></div>

               <div class="flex justify-between items-center mb-6 relative z-10">
                   <h2 class="text-lg font-bold text-white flex items-center gap-2">
                     <mat-icon class="text-cyan-400">playlist_add</mat-icon> Search Items
                   </h2>
                   <button mat-stroked-button class="!border-cyan-500/30 !text-cyan-400" (click)="addItem()">
                        <mat-icon>add</mat-icon> Add Input
                   </button>
               </div>

               <div class="space-y-4 relative z-10 max-h-[600px] overflow-y-auto custom-scrollbar pr-2">
                  <div *ngFor="let item of items(); let i = index" class="p-4 bg-[#0d1218] rounded-xl border border-white/5 relative group/item">
                      <div class="absolute top-2 right-2 opacity-0 group-hover/item:opacity-100 transition-opacity">
                          <button mat-icon-button color="warn" class="scale-75" (click)="removeItem(i)" [disabled]="items().length === 1">
                              <mat-icon>close</mat-icon>
                          </button>
                      </div>

                      <div class="grid grid-cols-1 gap-3">
                          <!-- Entity Type Select -->
                          <div class="w-full">
                              <label class="text-xs font-mono text-gray-500 uppercase tracking-wider ml-1 mb-1 block">Entity Type</label>
                              <mat-form-field appearance="outline" class="w-full custom-dark-field density-compact">
                                <mat-select [(ngModel)]="item.entity" placeholder="Select Type">
                                  <mat-option value="datasources">Datasource</mat-option>
                                  <mat-option value="tables">Table</mat-option>
                                  <mat-option value="columns">Column</mat-option>
                                  <mat-option value="metrics">Metric</mat-option>
                                  <mat-option value="golden_sql">Golden SQL</mat-option>
                                  <mat-option value="edges">Edge</mat-option>
                                  <mat-option value="context_rules">Context Rule</mat-option>
                                  <mat-option value="low_cardinality_values">Low Cardinality Value</mat-option>
                                </mat-select>
                                <mat-icon matPrefix class="text-gray-500 mr-2 scale-75">category</mat-icon>
                              </mat-form-field>
                          </div>

                          <!-- Search Text -->
                          <div class="w-full">
                              <label class="text-xs font-mono text-gray-500 uppercase tracking-wider ml-1 mb-1 block">Search Query</label>
                              <mat-form-field appearance="outline" class="w-full custom-dark-field density-compact">
                                <input matInput [(ngModel)]="item.search_text" placeholder="e.g. revenue users" (keydown.enter)="resolve()">
                                <mat-icon matSuffix class="text-gray-500 scale-75">search</mat-icon>
                              </mat-form-field>
                          </div>
                      </div>
                  </div>
               </div>

               <div class="pt-6 mt-4 border-t border-white/5 relative z-10">
                 <button mat-flat-button color="primary" class="w-full !h-12 !rounded-xl !text-base shadow-[0_0_20px_rgba(6,182,212,0.4)] hover:shadow-[0_0_30px_rgba(6,182,212,0.6)] !bg-cyan-600 transition-all"
                     (click)="resolve()" [disabled]="loading()">
                     <mat-icon *ngIf="!loading()" class="mr-2">play_arrow</mat-icon>
                     <mat-progress-spinner *ngIf="loading()" mode="indeterminate" diameter="20" class="mr-2 inline-block"></mat-progress-spinner>
                     <span *ngIf="!loading()">RESOLVE CONTEXT</span>
                     <span *ngIf="loading()">RESOLVING...</span>
                 </button>
               </div>
            </div>
          </div>

          <!-- Right Panel: Graph Results -->
          <div class="lg:col-span-7">
            <div class="bg-[#141a23] rounded-2xl border border-white/5 h-full min-h-[500px] flex flex-col shadow-xl overflow-hidden relative">
               
               <!-- Toolbar -->
               <div class="px-6 py-4 border-b border-white/5 flex justify-between items-center bg-[#0d1218]">
                  <div class="flex items-center gap-2">
                     <h2 class="text-lg font-bold text-white">Resolved Graph</h2>
                     <span *ngIf="hasSearched()" class="bg-green-500/10 text-green-400 text-xs px-2 py-0.5 rounded border border-green-500/20 font-mono">
                        {{ resultTime() }}ms
                     </span>
                     <span *ngIf="hasSearched()" class="bg-cyan-500/10 text-cyan-400 text-xs px-2 py-0.5 rounded border border-cyan-500/20 font-mono">
                        {{ resultGraph()?.graph?.length || 0 }} Datasources
                     </span>
                  </div>
                  <div class="flex gap-2">
                     <button mat-icon-button class="!text-gray-500 hover:!text-white transition-colors" matTooltip="Copy JSON" (click)="copyResults()">
                        <mat-icon class="text-sm">content_copy</mat-icon>
                     </button>
                     <button mat-icon-button class="!text-gray-500 hover:!text-white transition-colors" matTooltip="Clear" (click)="clearResults()">
                        <mat-icon class="text-sm">delete_outline</mat-icon>
                     </button>
                  </div>
               </div>

               <!-- Content Area -->
               <div class="flex-1 relative overflow-auto custom-scrollbar bg-[#0d1218]">
                   <!-- Loading State -->
                   <div *ngIf="loading()" class="absolute inset-0 z-20 flex flex-col items-center justify-center bg-[#0d1218]/80 backdrop-blur-sm">
                       <mat-progress-spinner mode="indeterminate" diameter="50" color="accent"></mat-progress-spinner>
                       <p class="mt-4 text-cyan-400 font-mono text-sm animate-pulse">Inferencing & Building Graph...</p>
                   </div>
                   
                   <!-- Empty State (Intro) -->
                   <div *ngIf="!hasSearched() && !loading()" class="h-full flex flex-col items-center justify-center text-center p-12 opacity-50">
                       <div class="p-6 bg-white/5 rounded-full mb-6 animate-float">
                          <mat-icon class="text-5xl text-gray-600 scale-150">hub</mat-icon>
                       </div>
                       <h3 class="text-xl font-bold text-gray-300">Context Graph</h3>
                       <p class="text-gray-500 max-w-sm mt-2">Add search items to see the resolved hierarchical schema context.</p>
                   </div>

                   <!-- Empty State (No Results) -->
                   <div *ngIf="hasSearched() && resultGraph()?.graph?.length === 0 && !loading()" class="h-full flex flex-col items-center justify-center text-center p-12">
                       <mat-icon class="text-5xl text-gray-700 mb-4">search_off</mat-icon>
                       <h3 class="text-lg font-bold text-gray-400">No context resolved</h3>
                       <p class="text-gray-600 mt-2">Try different search terms or types.</p>
                   </div>

                   <!-- JSON View -->
                   <div *ngIf="hasSearched() && resultGraph()?.graph?.length && !loading()" class="p-6">
                       <pre class="font-mono text-sm text-cyan-300 leading-relaxed bg-[#0a0e14] p-6 rounded-xl border border-white/5 shadow-inner overflow-x-auto selection:bg-cyan-500/30 selection:text-white">{{ resultGraph() | json }}</pre>
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
    /* Custom Scrollbar */
    .custom-scrollbar::-webkit-scrollbar { width: 8px; height: 8px; }
    .custom-scrollbar::-webkit-scrollbar-track { background: #0d1218; }
    .custom-scrollbar::-webkit-scrollbar-thumb { background: #2d3748; border-radius: 4px; }
    .custom-scrollbar::-webkit-scrollbar-thumb:hover { background: #4a5568; }

    /* Input Overrides */
    ::ng-deep .custom-dark-field .mat-mdc-text-field-wrapper {
        background-color: #0d1218 !important;
        border-radius: 8px !important;
        border: 1px solid rgba(255, 255, 255, 0.05);
    }
    ::ng-deep .custom-dark-field.density-compact .mat-mdc-text-field-wrapper {
        padding-top: 0 !important;
        padding-bottom: 0 !important;
        height: 48px; 
    }
    ::ng-deep .custom-dark-field .mat-mdc-form-field-icon-prefix > .mat-icon,
    ::ng-deep .custom-dark-field .mat-mdc-form-field-icon-suffix > .mat-icon {
        color: #718096 !important;
    }
    ::ng-deep .custom-dark-field .mat-mdc-input-element {
        color: #e2e8f0 !important;
    }
    ::ng-deep .custom-dark-field.mat-focused .mat-mdc-text-field-wrapper {
        border-color: rgba(6, 182, 212, 0.5) !important;
    }
    ::ng-deep .custom-dark-field .mat-mdc-floating-label { color: #718096 !important; }
    ::ng-deep .custom-dark-field.mat-focused .mat-mdc-floating-label { color: #22d3ee !important; }

    /* Select Panel Override */
    ::ng-deep .mat-mdc-select-panel { background-color: #1a202c !important; }
    ::ng-deep .mat-mdc-option { color: #e2e8f0 !important; }
    ::ng-deep .mat-mdc-option:hover { background-color: rgba(255, 255, 255, 0.05) !important; }
    ::ng-deep .mat-mdc-option.mdc-list-item--selected { color: #22d3ee !important; background-color: rgba(34, 211, 238, 0.1) !important; }
    
    .animate-float { animation: float 6s ease-in-out infinite; }
    @keyframes float {
        0% { transform: translateY(0px); }
        50% { transform: translateY(-10px); }
        100% { transform: translateY(0px); }
    }
    `]
})
export class ResolveContextPlaygroundComponent {
    private discoveryService = inject(DiscoveryService);

    // List of input items
    items = signal<ContextSearchItem[]>([
        { entity: 'tables', search_text: '' }
    ]);

    // Results
    resultGraph = signal<ContextResolutionResponse | null>(null);
    resultTime = signal<number | null>(null);
    loading = signal<boolean>(false);
    error = signal<string | null>(null);
    hasSearched = signal<boolean>(false);

    addItem() {
        this.items.update(items => [...items, { entity: 'tables', search_text: '' }]);
    }

    removeItem(index: number) {
        this.items.update(items => items.filter((_, i) => i !== index));
    }

    clearResults() {
        this.resultGraph.set(null);
        this.error.set(null);
        this.hasSearched.set(false);
    }

    copyResults() {
        if (this.resultGraph()) {
            navigator.clipboard.writeText(JSON.stringify(this.resultGraph(), null, 2));
        }
    }

    resolve() {
        if (this.items().some(i => !i.search_text.trim())) {
            // Optional: warn user that empty queries might be ignored or return generic results
            // But let's proceed.
        }

        this.loading.set(true);
        this.error.set(null);
        this.resultGraph.set(null);

        const start = performance.now();

        this.discoveryService.resolveContext(this.items()).subscribe({
            next: (data) => {
                this.resultGraph.set(data);
                this.resultTime.set(Math.round(performance.now() - start));
                this.hasSearched.set(true);
                this.loading.set(false);
            },
            error: (err) => {
                console.error(err);
                this.error.set(err.message || 'Error resolving context');
                this.loading.set(false);
            }
        });
    }
}
