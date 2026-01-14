
import { Component, ElementRef, ViewChild, signal, AfterViewInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatButtonToggleModule } from '@angular/material/button-toggle';
import { MatSelectModule } from '@angular/material/select';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatSnackBar } from '@angular/material/snack-bar';
import cytoscape from 'cytoscape';

import { DiscoveryService, GraphPathResult } from '../../../core/services/discovery.service';

@Component({
  selector: 'app-search-paths',
  standalone: true,
  imports: [
    CommonModule, FormsModule,
    MatFormFieldModule, MatInputModule, MatButtonModule,
    MatFormFieldModule, MatInputModule, MatButtonModule,
    MatIconModule, MatProgressSpinnerModule, MatButtonToggleModule, MatTooltipModule,
    MatSelectModule
  ],
  template: `
    <div class="h-full w-full bg-[#0a0e14] flex flex-col overflow-y-auto custom-scrollbar relative">
      
      <!-- HEADER & CONTROLS -->
      <div class="p-6 shrink-0 grid grid-cols-12 gap-8">
        
        <!-- Search Form -->
        <div class="col-span-12 bg-[#141a23] border border-gray-800 rounded-lg p-6">
          <div class="flex flex-col gap-6">
            
            <div class="flex justify-between items-center border-b border-gray-800 pb-4">
               <div>
                  <h3 class="text-white font-bold text-lg flex items-center gap-2">
                    <mat-icon class="text-indigo-500">route</mat-icon>
                    Path Finder
                  </h3>
                  <p class="text-xs text-gray-500 mt-1">Find traversal paths between two tables in the Knowledge Graph</p>
               </div>
               
               <div class="flex items-center gap-4">
                 <mat-button-toggle-group [(ngModel)]="viewMode" class="tech-toggle">
                    <mat-button-toggle value="graph" aria-label="Graph View">
                      <mat-icon>hub</mat-icon>
                    </mat-button-toggle>
                    <mat-button-toggle value="json" aria-label="JSON View">
                      <mat-icon>code</mat-icon>
                    </mat-button-toggle>
                 </mat-button-toggle-group>
               </div>
            </div>

            <div class="grid grid-cols-1 md:grid-cols-4 gap-4 items-end">
              
              <div class="flex flex-col gap-1">
                <label class="text-[10px] uppercase text-gray-500 font-bold ml-1">Datasource (Optional)</label>
                <mat-form-field appearance="outline" class="w-full tech-input">
                  <mat-icon matPrefix class="text-gray-600 scale-75 mr-2">storage</mat-icon>
                  <mat-select [(ngModel)]="selectedDatasourceSlug" (selectionChange)="onDatasourceChange()" placeholder="Any Datasource">
                     <mat-option [value]="null">All Datasources</mat-option>
                     <mat-option *ngFor="let ds of datasources" [value]="ds.slug">
                        {{ ds.name }} <span class="text-xs text-gray-500 ml-2">({{ ds.slug }})</span>
                     </mat-option>
                  </mat-select>
                </mat-form-field>
              </div>

              <div class="flex flex-col gap-1" *ngIf="selectedDatasourceSlug">
                <label class="text-[10px] uppercase text-gray-500 font-bold ml-1">Source Table</label>
                <mat-form-field appearance="outline" class="w-full tech-input">
                  <mat-icon matPrefix class="text-gray-600 scale-75 mr-2">table_chart</mat-icon>
                  <mat-select [(ngModel)]="sourceSlug" placeholder="Select Source">
                     <mat-option *ngFor="let table of tables" [value]="table.slug">
                        {{ table.physical_name }}
                     </mat-option>
                  </mat-select>
                </mat-form-field>
              </div>

              <div class="flex flex-col gap-1" *ngIf="!selectedDatasourceSlug">
                <label class="text-[10px] uppercase text-gray-500 font-bold ml-1">Source Table (Slug)</label>
                <mat-form-field appearance="outline" class="w-full tech-input">
                  <mat-icon matPrefix class="text-gray-600 scale-75 mr-2">table_chart</mat-icon>
                  <input matInput [(ngModel)]="sourceSlug" placeholder="e.g. orders" (keyup.enter)="search()">
                </mat-form-field>
              </div>

              <div class="flex flex-col gap-1" *ngIf="selectedDatasourceSlug">
                <label class="text-[10px] uppercase text-gray-500 font-bold ml-1">Target Table</label>
                <mat-form-field appearance="outline" class="w-full tech-input">
                  <mat-icon matPrefix class="text-gray-600 scale-75 mr-2">table_chart</mat-icon>
                  <mat-select [(ngModel)]="targetSlug" placeholder="Select Target">
                     <mat-option *ngFor="let table of tables" [value]="table.slug">
                        {{ table.physical_name }}
                     </mat-option>
                  </mat-select>
                </mat-form-field>
              </div>

              <div class="flex flex-col gap-1" *ngIf="!selectedDatasourceSlug">
                <label class="text-[10px] uppercase text-gray-500 font-bold ml-1">Target Table (Slug)</label>
                <mat-form-field appearance="outline" class="w-full tech-input">
                  <mat-icon matPrefix class="text-gray-600 scale-75 mr-2">table_chart</mat-icon>
                  <input matInput [(ngModel)]="targetSlug" placeholder="e.g. customers" (keyup.enter)="search()">
                </mat-form-field>
              </div>

              <div class="flex flex-col gap-1">
                 <label class="text-[10px] uppercase text-gray-500 font-bold ml-1">Max Depth</label>
                 <div class="flex items-center gap-2">
                    <mat-form-field appearance="outline" class="w-24 tech-input">
                      <input matInput type="number" [(ngModel)]="maxDepth" min="1" max="5">
                    </mat-form-field>
                    <button mat-icon-button (click)="maxDepth = maxDepth - 1" [disabled]="maxDepth <= 1" class="border border-gray-700 rounded bg-[#0f1218]">
                        <mat-icon>remove</mat-icon>
                    </button>
                    <button mat-icon-button (click)="maxDepth = maxDepth + 1" [disabled]="maxDepth >= 5" class="border border-gray-700 rounded bg-[#0f1218]">
                        <mat-icon>add</mat-icon>
                    </button>
                 </div>
              </div>

              <div class="flex gap-2">
                <button mat-flat-button color="primary" class="h-[52px] flex-1 !rounded text-base font-bold tracking-wide" 
                        [disabled]="loading || !sourceSlug || !targetSlug" (click)="search()">
                    <mat-icon class="mr-2" *ngIf="!loading">search</mat-icon>
                    <mat-spinner diameter="20" *ngIf="loading" class="mr-2 inline-block"></mat-spinner>
                    {{ loading ? 'SEARCHING...' : 'FIND PATHS' }}
                </button>
              </div>

            </div>
          </div>
        </div>

      </div>

      <!-- RESULTS AREA -->
      <div class="flex-1 px-6 pb-6 min-h-0 flex flex-col">
        
        <!-- GRAPH VIEW -->
        <div class="h-full w-full bg-[#141a23] rounded-lg border border-gray-800 flex flex-col relative overflow-hidden shadow-xl"
             [class.hidden]="viewMode !== 'graph'">
             
             <!-- Overlay if no result -->
             <div *ngIf="!result && !loading" class="absolute inset-0 flex flex-col items-center justify-center text-gray-600 z-10 pointer-events-none">
                <mat-icon class="text-6xl items-center justify-center opacity-20 w-24 h-24 text-[6rem]">hub</mat-icon>
                <div class="text-sm font-mono mt-4 uppercase tracking-widest opacity-50">Enter tables to visualize paths</div>
             </div>

             <div #cy class="h-full w-full block bg-[#0a0e14]/50"></div>
             
             <div class="absolute bottom-4 right-4 bg-[#0a0e14]/80 backdrop-blur border border-white/5 px-3 py-1.5 rounded text-[9px] text-gray-500 font-mono select-none pointer-events-none flex items-center gap-2">
                <mat-icon class="text-[10px] h-3 w-3 text-gray-600">touch_app</mat-icon>
                SCROLL TO ZOOM • DRAG TO PAN
             </div>
             
             <div *ngIf="result" class="absolute top-4 right-4 bg-[#0a0e14]/90 border border-indigo-500/30 px-4 py-2 rounded text-xs text-indigo-400 font-mono pointer-events-none">
                <span class="text-white font-bold">{{ result.total_paths }}</span> PORTHS FOUND
             </div>
        </div>

        <!-- JSON VIEW -->
        <div class="h-full w-full bg-[#0f1218] rounded-lg border border-gray-800 overflow-auto p-4 custom-scrollbar"
             *ngIf="viewMode === 'json'">
             <pre class="text-xs font-mono text-green-400 whitespace-pre-wrap">{{ result | json }}</pre>
        </div>

      </div>

    </div>
  `,
  styles: [`
    :host { 
        display: block; 
        height: 100%;
        width: 100%;
        overflow: hidden;
    }
  `]
})
export class SearchPathsComponent implements AfterViewInit, OnDestroy {

  sourceSlug = '';
  targetSlug = '';
  maxDepth = 3;
  viewMode: 'graph' | 'json' = 'graph';
  loading = false;

  selectedDatasourceSlug: string | null = null;
  datasources: any[] = [];
  tables: any[] = [];

  result: GraphPathResult | null = null;

  @ViewChild('cy') cyElement!: ElementRef;
  private cy: cytoscape.Core | null = null;

  constructor(
    private discoveryService: DiscoveryService,
    private snackBar: MatSnackBar
  ) { }

  ngAfterViewInit() {
    this.initGraph();
    this.loadDatasources();
  }

  loadDatasources() {
    this.discoveryService.searchDatasources({ query: '', limit: 100 }).subscribe({
      next: (res) => this.datasources = res.items,
      error: (err) => console.error('Error loading datasources', err)
    });
  }

  onDatasourceChange() {
    this.sourceSlug = '';
    this.targetSlug = '';
    this.tables = [];

    if (this.selectedDatasourceSlug) {
      this.loadTables(this.selectedDatasourceSlug);
    }
  }

  loadTables(dsSlug: string) {
    this.discoveryService.searchTables({
      query: '',
      datasource_slug: dsSlug,
      limit: 1000 // Ensure we get enough tables
    }).subscribe({
      next: (res) => this.tables = res.items,
      error: (err) => console.error('Error loading tables', err)
    });
  }

  ngOnDestroy() {
    if (this.cy) this.cy.destroy();
  }

  search() {
    if (!this.sourceSlug || !this.targetSlug) return;

    this.loading = true;
    this.discoveryService.searchPaths({
      source_table_slug: this.sourceSlug,
      target_table_slug: this.targetSlug,
      datasource_slug: this.selectedDatasourceSlug || undefined,
      max_depth: this.maxDepth
    }).subscribe({
      next: (res) => {
        this.result = res;
        this.loading = false;

        if (this.viewMode === 'graph') {
          // Short delay to ensure view is visible/rendered
          setTimeout(() => this.visualizePaths(res), 50);
        }
      },
      error: (err) => {
        console.error('Error searching paths', err);
        this.loading = false;
        this.snackBar.open('Error finding paths: ' + (err.error?.detail || err.message), 'Dismiss', { duration: 3000 });
      }
    });
  }

  initGraph() {
    if (!this.cyElement) return;

    this.cy = cytoscape({
      container: this.cyElement.nativeElement,
      boxSelectionEnabled: false,
      autounselectify: true,
      style: [
        // Copying styles from DatasourceGraphComponent
        {
          selector: 'node',
          style: {
            'label': 'data(label)',
            'text-valign': 'center',
            'text-halign': 'center',
            'background-color': '#0f172a',
            'border-width': 1,
            'border-color': '#3b82f6',
            'border-opacity': 0.8,
            'width': 'label',
            'height': 'label',
            'padding': '16px',
            'shape': 'round-rectangle',
            'color': '#f8fafc',
            'font-size': '12px',
            'font-family': 'Inter, system-ui, sans-serif',
            'font-weight': 600,
            'text-transform': 'uppercase',
            'text-max-width': '180px',
            'text-wrap': 'wrap'
          } as any
        },
        {
          selector: 'edge',
          style: {
            'width': 2,
            'line-color': '#334155',
            'target-arrow-color': '#334155',
            'target-arrow-shape': 'triangle',
            'curve-style': 'bezier',
            'label': 'data(label)',
            'font-size': '10px',
            'color': '#94a3b8',
            'text-rotation': 'autorotate',
            'text-background-opacity': 1,
            'text-background-color': '#0a0e14',
            'text-background-padding': '2px'
          } as any
        }
      ],
      layout: { name: 'grid' }
    });
  }

  visualizePaths(data: GraphPathResult) {
    if (!this.cy) return;
    this.cy.elements().remove();

    if (!data.paths || data.paths.length === 0) return;

    const addedNodes = new Set<string>();
    const elements: any[] = [];

    // Process each path
    data.paths.forEach((path: any[], pathIdx: number) => {
      // path is List<GraphEdge>
      path.forEach((edge: any) => {
        // Source Node
        const srcId = `node-${edge.source.table_slug}`;
        if (!addedNodes.has(srcId)) {
          elements.push({
            group: 'nodes',
            data: {
              id: srcId,
              label: edge.source.table_name,
              slug: edge.source.table_slug
            }
          });
          addedNodes.add(srcId);
        }

        // Target Node
        const tgtId = `node-${edge.target.table_slug}`;
        if (!addedNodes.has(tgtId)) {
          elements.push({
            group: 'nodes',
            data: {
              id: tgtId,
              label: edge.target.table_name,
              slug: edge.target.table_slug
            }
          });
          addedNodes.add(tgtId);
        }

        // Edge
        const edgeId = `edge-${srcId}-${tgtId}-${pathIdx}`; // Unique edge per path instance if shared?
        // Actually, if same edge exists multiple times (in different paths), we might want to show it once?
        // Or show multiple edges if they represent different paths?
        // Graph visualization usually unifies.
        // Let's unify edges based on source-target-relationship.

        const uniqueEdgeId = `edge-${edge.source.table_slug}-${edge.target.table_slug}-${edge.relationship_type}`;
        // We can just add it. Cytoscape handles duplicates if ID matches.
        // But we want to allow multiple edges if they are different relationships.

        elements.push({
          group: 'edges',
          data: {
            id: uniqueEdgeId,
            source: srcId,
            target: tgtId,
            label: edge.relationship_type
          }
        });
      });
    });

    this.cy.add(elements);

    // Layout
    const layout = this.cy.layout({
      name: 'cose',
      animate: true,
      animationDuration: 1000,
      nodeDimensionsIncludeLabels: true,
      randomize: false,
      componentSpacing: 100,
      nodeRepulsion: (node: any) => 8000,
      idealEdgeLength: (edge: any) => 150,
      nestingFactor: 5,
      gravity: 0.25,
      numIter: 1000
    } as any);

    layout.run();
    this.cy.fit(undefined, 50);
  }
}
