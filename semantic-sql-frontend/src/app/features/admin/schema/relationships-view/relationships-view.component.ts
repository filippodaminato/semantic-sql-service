import { Component, Input, OnInit, OnChanges, SimpleChanges, signal } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { CommonModule } from '@angular/common';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatTableModule } from '@angular/material/table';
import { MatDialog } from '@angular/material/dialog';
import { MatTooltipModule } from '@angular/material/tooltip';
import { AdminService } from '../../../../core/services/admin.service';
import { Table } from '../../../../core/models/admin.models';
import { CreateRelationshipDialogComponent } from './create-relationship-dialog.component';

@Component({
    selector: 'app-relationships-view',
    standalone: true,
    imports: [
        CommonModule,
        MatButtonModule, MatIconModule, MatTableModule, MatTooltipModule
    ],
    template: `
    <div class="h-full flex flex-col p-6 max-w-6xl mx-auto">
      <div class="flex justify-between items-center mb-6">
        <div>
           <h2 class="text-xl font-bold text-gray-200">Relationships</h2>
           <p class="text-gray-500 text-sm">Define how tables are linked in this datasource</p>
        </div>
        
        <button mat-flat-button color="primary" (click)="openCreateDialog()" [disabled]="loading()">
            <mat-icon>add_link</mat-icon> NEW RELATIONSHIP
        </button>
      </div>
      
      <div *ngIf="loading()" class="p-8 text-center text-gray-500">
           Loading...
      </div>

      <div *ngIf="!loading()" class="rounded-lg border border-gray-700 overflow-auto max-h-[calc(100vh-250px)] bg-[#141a23]">
        <table mat-table [dataSource]="relationships" class="w-full bg-[#141a23]">
          
          <!-- Source Column -->
          <ng-container matColumnDef="source">
            <th mat-header-cell *matHeaderCellDef> Source </th>
            <td mat-cell *matCellDef="let rel"> 
                <span class="text-blue-400 font-mono">{{rel.source_table}}</span>.{{rel.source_column}} 
            </td>
          </ng-container>

          <!-- Type Column -->
          <ng-container matColumnDef="type">
            <th mat-header-cell *matHeaderCellDef class="w-[150px] text-center"> Type </th>
            <td mat-cell *matCellDef="let rel" class="text-center">
                 <span class="px-2 py-1 rounded bg-slate-800 text-xs font-bold text-gray-400 border border-slate-700">
                    {{rel.relationship_type}}
                 </span>
            </td>
          </ng-container>

          <!-- Target Column -->
          <ng-container matColumnDef="target">
            <th mat-header-cell *matHeaderCellDef> Target </th>
            <td mat-cell *matCellDef="let rel"> 
                 <span class="text-green-400 font-mono">{{rel.target_table}}</span>.{{rel.target_column}} 
            </td>
          </ng-container>

          <!-- Description Column -->
          <ng-container matColumnDef="description">
            <th mat-header-cell *matHeaderCellDef class="hidden md:table-cell"> Description </th>
            <td mat-cell *matCellDef="let rel" class="hidden md:table-cell text-gray-400 text-xs italic max-w-[200px] truncate" [matTooltip]="rel.description"> 
                 {{rel.description || '-'}} 
            </td>
          </ng-container>

          <!-- Context Note Column -->
          <ng-container matColumnDef="context_note">
             <th mat-header-cell *matHeaderCellDef class="hidden lg:table-cell"> Context </th>
             <td mat-cell *matCellDef="let rel" class="hidden lg:table-cell text-gray-500 text-xs max-w-[150px] truncate" [matTooltip]="rel.context_note">
                 {{rel.context_note || '-'}}
             </td>
          </ng-container>
          
           <!-- Inferred Column -->
          <ng-container matColumnDef="inferred">
            <th mat-header-cell *matHeaderCellDef class="w-[100px] text-center"> Origin </th>
            <td mat-cell *matCellDef="let rel" class="text-center">
                <mat-icon *ngIf="rel.is_inferred" class="text-purple-400 text-sm" matTooltip="Auto-Inferred">auto_awesome</mat-icon>
                <mat-icon *ngIf="!rel.is_inferred" class="text-gray-600 text-sm" matTooltip="Manually Defined">edit</mat-icon>
            </td>
          </ng-container>

          <!-- Actions -->
           <ng-container matColumnDef="actions">
            <th mat-header-cell *matHeaderCellDef class="w-[80px]"></th>
            <td mat-cell *matCellDef="let rel">
                <button mat-icon-button color="primary" (click)="openCreateDialog(rel)" class="mr-2">
                    <mat-icon>edit</mat-icon>
                </button>
                <button mat-icon-button color="warn" (click)="deleteRelationship(rel)"> 
                    <mat-icon>delete</mat-icon>
                </button>
            </td>
          </ng-container>

          <tr mat-header-row *matHeaderRowDef="displayedColumns; sticky: true"></tr>
          <tr mat-row *matRowDef="let row; columns: displayedColumns;" class="hover:bg-slate-800/30"></tr>
        </table>
        
        <div *ngIf="relationships.length === 0" class="p-8 text-center text-gray-500">
            No relationships found.
        </div>
      </div>
    </div>
  `,
    styles: [`
    .mat-mdc-table { background: transparent; }
    .mat-mdc-header-row { background: #1e293b; }
    .mat-mdc-header-cell { color: #94a3b8; border-bottom: 1px solid #334155; }
    .mat-mdc-cell { color: #e2e8f0; border-bottom: 1px solid #1e293b; }
  `]
})
export class RelationshipsViewComponent implements OnInit, OnChanges {
    @Input() datasourceId: string | null = null;

    relationships: any[] = [];
    tables: Table[] = [];
    loading = signal<boolean>(false);

    displayedColumns = ['source', 'type', 'target', 'description', 'context_note', 'inferred', 'actions'];

    constructor(private adminService: AdminService, private dialog: MatDialog, private route: ActivatedRoute) { }

    ngOnInit() {
        if (!this.datasourceId) {
            this.route.parent?.paramMap.subscribe(params => {
                const id = params.get('id');
                if (id) {
                    this.datasourceId = id;
                    this.loadRelationships();
                }
            });
        } else {
            this.loadRelationships();
        }
    }

    ngOnChanges(changes: SimpleChanges) {
        if (changes['datasourceId'] && this.datasourceId) {
            this.loadRelationships();
        }
    }

    loadRelationships() {
        if (!this.datasourceId) return;
        this.loading.set(true);

        // Load tables first to resolve names
        this.adminService.getTables(this.datasourceId).subscribe(tables => {
            this.tables = tables;

            if (tables.length === 0) {
                this.relationships = [];
                this.loading.set(false);
                return;
            }

            // Load all relationships for datasource in one go
            this.adminService.getDatasourceRelationships(this.datasourceId!).subscribe({
                next: (res: any[]) => {
                    this.processRelationships(res);
                },
                error: (err) => {
                    console.error('Error fetching relationships', err);
                    this.loading.set(false);
                }
            });
        });
    }

    processRelationships(rawRels: any[]) {
        // Map raw relationships to view model
        // Backend now provides resolved names directly, no need to lookup IDs
        this.relationships = rawRels.map(r => ({
            ...r,
            source_table: r.source_table || 'Unknown',
            source_column: r.source_column || 'Unknown',
            target_table: r.target_table || 'Unknown',
            target_column: r.target_column || 'Unknown'
        }));
        this.loading.set(false);
    }

    openCreateDialog(existingRel: any = null) {
        this.dialog.open(CreateRelationshipDialogComponent, {
            width: '600px',
            data: { tables: this.tables, relationship: existingRel }
        }).afterClosed().subscribe(result => {
            if (result) {
                if (existingRel) {
                    this.adminService.updateRelationship(existingRel.id, result).subscribe(() => {
                        this.loadRelationships();
                    });
                } else {
                    this.adminService.createRelationship(result).subscribe(() => {
                        this.loadRelationships();
                    });
                }
            }
        });
    }

    deleteRelationship(rel: any) {
        if (!confirm(`Are you sure you want to delete the relationship between ${rel.source_table}.${rel.source_column} and ${rel.target_table}.${rel.target_column}?`)) {
            return;
        }

        this.adminService.deleteRelationship(rel.id).subscribe({
            next: () => {
                this.loadRelationships();
            },
            error: (err) => console.error('Failed to delete relationship', err)
        });
    }
}
