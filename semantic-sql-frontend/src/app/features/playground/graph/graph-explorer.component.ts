import { Component, ElementRef, ViewChild, AfterViewInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { RetrievalService } from '../../../core/services/retrieval.service';
import cytoscape from 'cytoscape';

@Component({
    selector: 'app-graph-explorer',
    standalone: true,
    imports: [
        CommonModule,
        FormsModule,
        MatInputModule,
        MatButtonModule,
        MatProgressSpinnerModule
    ],
    template: `
        <div class="h-full w-full flex flex-col bg-[#050505] p-6 gap-4">
             <div class="flex gap-4 items-center">
                 <mat-form-field appearance="outline" class="w-64">
                    <mat-label>Datasource Slug</mat-label>
                    <input matInput [(ngModel)]="datasourceSlug" placeholder="e.g. ecommerce">
                 </mat-form-field>
                 
                 <mat-form-field appearance="outline" class="w-96">
                    <mat-label>Anchor Entities</mat-label>
                    <input matInput [(ngModel)]="anchorInput" placeholder="orders customers">
                 </mat-form-field>

                 <button mat-flat-button color="primary" (click)="visualize()" [disabled]="loading">
                    <span *ngIf="!loading">EXPLORE GRAPH</span>
                    <mat-spinner *ngIf="loading" diameter="20"></mat-spinner>
                 </button>
             </div>

             <div class="flex-1 relative rounded-xl border border-gray-800 overflow-hidden bg-black/50 shadow-inner">
                 <div #cy class="absolute inset-0 block"></div>
                 
                 <div *ngIf="!hasData && !loading" class="absolute inset-0 flex items-center justify-center text-gray-600 font-mono text-sm">
                    ENTER PARAMETERS TO VISUALIZE SUB-GRAPH
                 </div>
             </div>
        </div>
    `,
    styles: [`:host { display: block; height: 100%; }`]
})
export class GraphExplorerComponent implements AfterViewInit, OnDestroy {
    datasourceSlug = 'ecommerce';
    anchorInput = '';
    loading = false;
    hasData = false;

    @ViewChild('cy') cyElement!: ElementRef;
    private cy: cytoscape.Core | null = null;

    constructor(private retrievalService: RetrievalService) { }

    ngAfterViewInit() {
        this.initGraph();
    }

    ngOnDestroy() {
        if (this.cy) this.cy.destroy();
    }

    initGraph() {
        if (!this.cyElement) return;

        this.cy = cytoscape({
            container: this.cyElement.nativeElement,
            style: [
                {
                    selector: 'node',
                    style: {
                        'label': 'data(label)',
                        'text-valign': 'center',
                        'text-halign': 'center',
                        'background-color': '#0f172a',
                        'border-width': 1,
                        'border-color': '#3b82f6',
                        'color': '#f8fafc',
                        'width': 'label',
                        'height': 'label',
                        'padding': '12px',
                        'shape': 'round-rectangle',
                        'font-size': '12px',
                        'text-transform': 'uppercase'
                    } as any
                },
                {
                    selector: 'edge',
                    style: {
                        'width': 2,
                        'line-color': '#475569',
                        'target-arrow-color': '#475569',
                        'target-arrow-shape': 'triangle',
                        'curve-style': 'bezier'
                    } as any
                },
                {
                    selector: 'edge[label]',
                    style: {
                        'label': 'data(label)',
                        'font-size': '10px',
                        'color': '#94a3b8',
                        'text-background-opacity': 1,
                        'text-background-color': '#050505',
                        'text-background-padding': '2px'
                    } as any
                }
            ],
            layout: { name: 'grid' }
        });
    }

    visualize() {
        if (!this.anchorInput.trim() || !this.datasourceSlug.trim()) return;

        this.loading = true;
        const anchors = this.anchorInput.split(' ').filter(s => s.trim());

        this.retrievalService.expandGraph({
            datasource_slug: this.datasourceSlug,
            anchor_entities: anchors
        }).subscribe({
            next: (res) => {
                this.buildGraph(res, anchors);
                this.loading = false;
                this.hasData = true;
            },
            error: (err) => {
                console.error(err);
                this.loading = false;
            }
        });
    }

    buildGraph(res: any, anchors: string[]) {
        if (!this.cy) return;
        this.cy.elements().remove();

        // Nodes
        const tables = new Set<string>([...anchors, ...res.bridge_tables]);
        const nodes = Array.from(tables).map(t => ({
            data: { id: t, label: t }
        }));

        // Edges
        const edges = res.relationships.map((rel: any, i: number) => ({
            data: {
                id: `e-${i}`,
                source: rel.source_table,
                target: rel.target_table,
                label: rel.relationship_type
            }
        }));

        this.cy.add([...nodes, ...edges]);

        this.cy.layout({
            name: 'cose',
            animate: true,
            animationDuration: 800,
            padding: 50
        } as any).run();
    }
}
