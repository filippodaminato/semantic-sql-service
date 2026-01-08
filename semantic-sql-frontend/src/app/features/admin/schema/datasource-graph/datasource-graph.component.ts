import { Component, Input, OnInit, OnChanges, SimpleChanges, ElementRef, ViewChild, Output, EventEmitter, AfterViewInit, OnDestroy, signal, effect } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatSnackBar } from '@angular/material/snack-bar';
import { AdminService } from '../../../../core/services/admin.service';
import { Datasource } from '../../../../core/models/admin.models';
import cytoscape from 'cytoscape';

@Component({
    selector: 'app-datasource-graph',
    standalone: true,
    imports: [
        CommonModule, FormsModule,
        MatProgressSpinnerModule, MatFormFieldModule, MatInputModule, MatButtonModule, MatIconModule
    ],
    template: `
    <div class="h-full w-full bg-[#0a0e14] flex flex-col overflow-y-auto custom-scrollbar relative">
        
        <!-- DASHBOARD HEADER & EDIT FORM -->
        <div class="p-6 grid grid-cols-12 gap-8 shrink-0">
            
            <!-- Left: Edit Form -->
            <div class="col-span-8 bg-[#141a23] border border-gray-800 rounded-lg p-6">
                <div class="flex justify-between items-center mb-6 border-b border-gray-800 pb-2">
                    <h3 class="text-white font-bold text-lg flex items-center gap-2">
                        <mat-icon class="text-blue-500">settings</mat-icon>
                        Datasource Settings
                    </h3>
                    <button mat-flat-button color="primary" [disabled]="saving()" (click)="saveDatasource()">
                        <mat-icon *ngIf="!saving()">save</mat-icon>
                        <mat-spinner *ngIf="saving()" diameter="18" class="mr-2 inline-block"></mat-spinner>
                        {{ saving() ? 'SAVING...' : 'SAVE CHANGES' }}
                    </button>
                </div>

                <div class="grid grid-cols-2 gap-4" *ngIf="datasource">
                    <div class="flex flex-col gap-1">
                        <label class="text-[10px] uppercase text-gray-500 font-bold ml-1">Display Name</label>
                        <mat-form-field appearance="outline" class="w-full tech-input">
                            <input matInput [(ngModel)]="datasource.name" placeholder="e.g. Sales DWH">
                        </mat-form-field>
                    </div>

                    <div class="flex flex-col gap-1">
                         <label class="text-[10px] uppercase text-gray-500 font-bold ml-1">Engine</label>
                         <mat-form-field appearance="outline" class="w-full tech-input">
                             <input matInput [value]="datasource.engine" disabled class="text-gray-500">
                             <mat-icon matSuffix class="text-gray-600 scale-75">lock</mat-icon>
                         </mat-form-field>
                    </div>

                    <div class="col-span-2 flex flex-col gap-1">
                        <label class="text-[10px] uppercase text-gray-500 font-bold ml-1">Context Signature / System Prompt</label>
                         <mat-form-field appearance="outline" class="w-full tech-input">
                            <input matInput [(ngModel)]="datasource.context_signature" placeholder="Short description for the AI context...">
                            <mat-icon matSuffix class="text-yellow-500/70 scale-75" matTooltip="Used by AI to understand domain">lightbulb</mat-icon>
                        </mat-form-field>
                    </div>

                    <div class="col-span-2 flex flex-col gap-1">
                        <label class="text-[10px] uppercase text-gray-500 font-bold ml-1">Description</label>
                        <mat-form-field appearance="outline" class="w-full tech-input">
                            <textarea matInput [(ngModel)]="datasource.description" rows="3" placeholder="Detailed description..."></textarea>
                        </mat-form-field>
                    </div>
                </div>
            </div>

            <!-- Right: Stats Dashboard -->
            <div class="col-span-4 flex flex-col gap-4">
                 <!-- Stats Card -->
                 <div class="bg-[#141a23] border border-gray-800 rounded-lg p-6 flex-1 flex flex-col">
                    <h3 class="text-gray-400 text-xs font-bold uppercase tracking-wider mb-4 border-b border-gray-800 pb-2">Overview Stats</h3>
                    
                    <div class="grid grid-cols-2 gap-4 flex-1 content-start">
                        <div class="bg-[#0f1218] rounded p-4 border border-gray-800 flex flex-col items-center justify-center relative overflow-hidden group">
                             <div class="absolute inset-0 bg-blue-500/5 group-hover:bg-blue-500/10 transition-colors"></div>
                             <span class="text-3xl font-bold text-white">{{nodeCount}}</span>
                             <span class="text-[10px] text-gray-500 uppercase tracking-widest mt-1">Total Nodes</span>
                        </div>
                        <div class="bg-[#0f1218] rounded p-4 border border-gray-800 flex flex-col items-center justify-center relative overflow-hidden group">
                             <div class="absolute inset-0 bg-indigo-500/5 group-hover:bg-indigo-500/10 transition-colors"></div>
                             <span class="text-3xl font-bold text-white">{{edgeCount}}</span>
                             <span class="text-[10px] text-gray-500 uppercase tracking-widest mt-1">Relationships</span>
                        </div>
                         <!-- Placeholder for more stats -->
                        <div class="bg-[#0f1218] rounded p-4 border border-gray-800 flex flex-col items-center justify-center col-span-2 relative overflow-hidden group">
                             <div class="absolute inset-0 bg-green-500/5 group-hover:bg-green-500/10 transition-colors"></div>
                             <span class="text-xl font-mono text-gray-300">{{datasource?.slug || 'N/A'}}</span>
                             <span class="text-[10px] text-gray-500 uppercase tracking-widest mt-1">API Slug</span>
                        </div>
                    </div>
                 </div>
            </div>
        </div>

        <!-- GRAPH CARD -->
        <div class="px-6 pb-6 flex-1 flex flex-col h-[120vh] min-h-[800px]">
             <div class="h-full w-full bg-[#141a23] rounded-lg border border-gray-800 flex flex-col relative overflow-hidden shadow-xl">
                 
                 <!-- Graph Header -->
                 <div class="absolute top-0 left-0 right-0 p-4 z-10 flex justify-between items-start pointer-events-none bg-gradient-to-b from-[#141a23] via-[#141a23]/80 to-transparent">
                     <div>
                         <h3 class="text-white font-bold text-lg tracking-tight drop-shadow-[0_2px_4px_rgba(0,0,0,0.5)] flex items-center gap-2">
                             <mat-icon class="text-indigo-500 scale-90">hub</mat-icon>
                             Schema Topology
                         </h3>
                         <p class="text-[10px] text-gray-400 font-mono ml-8 uppercase tracking-wider">Interactive Knowledge Graph</p>
                     </div>
                 </div>

                 <!-- Loading Overlay -->
                <div *ngIf="loading" class="absolute inset-0 flex flex-col gap-4 items-center justify-center z-50 bg-[#141a23]/90 backdrop-blur-sm transition-opacity duration-300">
                    <mat-spinner diameter="40" color="accent"></mat-spinner>
                    <div class="text-xs text-blue-400 font-mono tracking-widest animate-pulse">GENERATING VISUALIZATION...</div>
                </div>

                <!-- Actual Graph Container -->
                <div #cy class="h-full w-full block bg-[#0a0e14]/50"></div>
                 
                 <!-- Controls Hint -->
                <div class="absolute bottom-4 right-4 bg-[#0a0e14]/80 backdrop-blur border border-white/5 px-3 py-1.5 rounded text-[9px] text-gray-500 font-mono select-none pointer-events-none flex items-center gap-2">
                    <mat-icon class="text-[10px] h-3 w-3 text-gray-600">touch_app</mat-icon>
                    SCROLL TO ZOOM • DRAG TO PAN
                </div>

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
export class DatasourceGraphComponent implements OnInit, AfterViewInit, OnChanges, OnDestroy {
    @Input() datasourceId: string | null = null;
    @Output() nodeSelected = new EventEmitter<string>();

    @ViewChild('cy') cyElement!: ElementRef;

    private cy: cytoscape.Core | null = null;

    datasource: Datasource | null = null;
    loading = false;
    saving = signal<boolean>(false);

    nodeCount = 0;
    edgeCount = 0;

    constructor(
        private adminService: AdminService,
        private route: ActivatedRoute,
        private snackBar: MatSnackBar
    ) { }

    ngOnInit() {
        if (!this.datasourceId) {
            this.route.parent?.paramMap.subscribe(params => {
                const id = params.get('id');
                if (id) {
                    this.datasourceId = id;
                    this.loadDatasourceDetails();
                }
            });
        }
    }

    ngAfterViewInit() {
        this.initGraph();
        if (this.datasourceId) {
            this.loadGraphData();
            if (!this.datasource) this.loadDatasourceDetails();
        }
    }

    ngOnChanges(changes: SimpleChanges) {
        if (changes['datasourceId'] && this.datasourceId) {
            this.loadDatasourceDetails();
            if (this.cy) this.loadGraphData();
        }
    }

    ngOnDestroy() {
        if (this.cy) {
            this.cy.destroy();
        }
    }

    loadDatasourceDetails() {
        if (!this.datasourceId) return;
        this.adminService.getDatasource(this.datasourceId).subscribe({
            next: (ds) => this.datasource = ds,
            error: (err) => console.error('Error loading datasource', err)
        });
    }

    saveDatasource() {
        if (!this.datasourceId || !this.datasource) return;

        this.saving.set(true);
        const updateData = {
            name: this.datasource.name,
            description: this.datasource.description,
            context_signature: this.datasource.context_signature
        };

        this.adminService.updateDatasource(this.datasourceId, updateData).subscribe({
            next: (updated) => {
                this.datasource = updated;
                this.saving.set(false);
                this.snackBar.open('Datasource saved successfully!', 'Dismiss', { duration: 3000 });
            },
            error: (err) => {
                console.error('Error saving datasource', err);
                this.saving.set(false);
                this.snackBar.open('Error saving datasource', 'Dismiss', { duration: 3000 });
            }
        });
    }

    initGraph() {
        if (!this.cyElement) return;

        this.cy = cytoscape({
            container: this.cyElement.nativeElement,
            boxSelectionEnabled: false,
            autounselectify: true,

            // "Neon/Dark" Theme
            style: [
                {
                    selector: 'node',
                    style: {
                        'label': 'data(label)',
                        'text-valign': 'center',
                        'text-halign': 'center',
                        'background-color': '#0f172a',
                        'border-width': 1,
                        'border-color': '#3b82f6', // bright blue
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
                        'text-wrap': 'wrap',
                        'text-shadow-blur': 0,
                        'transition-property': 'background-color, border-color, shadow-blur',
                        'transition-duration': 300
                    } as any
                },
                {
                    selector: 'node:selected',
                    style: {
                        'background-color': '#1e293b',
                        'border-color': '#60a5fa',
                        'border-width': 2,
                        'shadow-blur': 20,
                        'shadow-color': '#3b82f6',
                        'shadow-opacity': 0.6
                    } as any
                },
                {
                    selector: '$node > node', // Compounds if any
                    style: {
                        'padding-top': '10px',
                        'padding-left': '10px',
                        'padding-bottom': '10px',
                        'padding-right': '10px',
                        'text-valign': 'top',
                        'text-halign': 'center',
                        'background-color': '#bbb'
                    } as any
                },
                {
                    selector: 'edge',
                    style: {
                        'width': 2,
                        'line-color': '#334155', // slate-700
                        'target-arrow-color': '#334155',
                        'target-arrow-shape': 'triangle',
                        'curve-style': 'bezier',
                        'arrow-scale': 1.0,
                        'opacity': 0.6
                    } as any
                },
                {
                    selector: 'edge:selected',
                    style: {
                        'line-color': '#60a5fa',
                        'target-arrow-color': '#60a5fa',
                        'width': 3,
                        'opacity': 1
                    } as any
                },
                // Improve edge label visibility
                {
                    selector: 'edge[label]',
                    style: {
                        'label': 'data(label)',
                        'font-size': '9px',
                        'color': '#94a3b8',
                        'text-background-opacity': 1,
                        'text-background-color': '#050505',
                        'text-background-padding': '4px',
                        'text-background-shape': 'roundrectangle'
                    } as any
                }
            ],

            // Initial layout (will be overridden by run)
            layout: {
                name: 'grid'
            }
        });

        this.cy.on('tap', 'node', (evt) => {
            const node = evt.target;
            const nodeId = node.id();
            // Assuming format "table-UUID"
            const parts = nodeId.split('-');
            if (parts.length >= 2 && parts[0] === 'table') {
                this.nodeSelected.emit(parts[1]);
            } else {
                this.nodeSelected.emit(nodeId);
            }
        });

        // Hover effects
        this.cy.on('mouseover', 'node', (evt) => {
            evt.target.style({
                'border-color': '#60a5fa',
                'shadow-blur': 15,
                'shadow-color': '#3b82f6',
                'shadow-opacity': 0.4,
                'cursor': 'pointer'
            });
        });

        this.cy.on('mouseout', 'node', (evt) => {
            evt.target.removeStyle();
        });
    }

    loadGraphData() {
        if (!this.datasourceId || !this.cy) return;

        this.loading = true;
        this.adminService.getGraph(this.datasourceId).subscribe({
            next: (response) => {
                if (!this.cy) return;

                this.cy.elements().remove();

                const nodes = response.nodes.map((n: any) => ({
                    data: {
                        id: n.id,
                        label: n.data.label || n.id,
                        ...n.data
                    }
                }));

                const edges = response.edges.map((e: any) => ({
                    data: {
                        id: e.id,
                        source: e.source,
                        target: e.target,
                        label: e.label
                    }
                }));

                this.cy.add([...nodes, ...edges]);

                this.nodeCount = nodes.length;
                this.edgeCount = edges.length;

                // Use 'cose' layout - Physics simulation for organic looks
                // No external dependencies needed!
                const layout = this.cy.layout({
                    name: 'cose',
                    animate: true,
                    animationDuration: 1000,
                    nodeDimensionsIncludeLabels: true,
                    randomize: true, // Start from random for better unfolding
                    componentSpacing: 100,
                    nodeRepulsion: (node: any) => 8000,
                    idealEdgeLength: (edge: any) => 100,
                    edgeElasticity: (edge: any) => 100,
                    nestingFactor: 5,
                    gravity: 0.25,
                    numIter: 1000,
                    initialTemp: 200,
                    minTemp: 1.0
                } as any);

                layout.run();
                this.cy.resize(); // Ensure generic resize

                this.loading = false;
            },
            error: (err) => {
                console.error('Error loading graph', err);
                this.loading = false;
            }
        });
    }
}
