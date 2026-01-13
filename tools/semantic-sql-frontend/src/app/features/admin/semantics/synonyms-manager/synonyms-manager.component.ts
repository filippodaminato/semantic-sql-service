import { Component, Input, OnInit, OnChanges, SimpleChanges, signal } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { CommonModule } from '@angular/common';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatTableModule } from '@angular/material/table';
import { MatChipsModule } from '@angular/material/chips';
import { MatDialog } from '@angular/material/dialog';
import { AdminService } from '../../../../core/services/admin.service';
import { Synonym } from '../../../../core/models/admin.models';
import { CreateSynonymDialogComponent } from './create-synonym-dialog.component';

@Component({
  selector: 'app-synonyms-manager',
  standalone: true,
  imports: [
    CommonModule,
    MatButtonModule, MatIconModule, MatTableModule, MatChipsModule
  ],
  template: `
    <div class="h-full flex flex-col p-6 max-w-6xl mx-auto">
      <div class="flex justify-between items-center mb-6">
        <div>
           <h2 class="text-xl font-bold text-gray-200">Synonyms</h2>
           <p class="text-gray-500 text-sm">Define alternative names for tables and columns for better NLP</p>
        </div>
        
        <button mat-flat-button color="primary" [disabled]="loading()" (click)="openAddDialog()"> 
            <mat-icon>add</mat-icon> ADD SYNONYMS
        </button>
      </div>
      
      <div *ngIf="loading()" class="p-8 text-center text-gray-500">Loading...</div>

      <div *ngIf="!loading()" class="rounded-lg border border-gray-700 overflow-auto max-h-[calc(100vh-250px)] bg-[#141a23]">
        <table mat-table [dataSource]="synonyms" class="w-full bg-[#141a23]">
          
          <ng-container matColumnDef="term">
            <th mat-header-cell *matHeaderCellDef> Synonym / Term </th>
            <td mat-cell *matCellDef="let s" class="font-bold text-gray-200"> {{s.term}} </td>
          </ng-container>

          <ng-container matColumnDef="target">
            <th mat-header-cell *matHeaderCellDef> Maps To </th>
            <td mat-cell *matCellDef="let s">
                <span class="text-gray-400 text-sm mr-2">{{s.target_type}}:</span>
                <span class="text-blue-400 font-mono">{{resolveTargetName(s)}}</span>
            </td>
          </ng-container>

          <ng-container matColumnDef="actions">
            <th mat-header-cell *matHeaderCellDef class="w-[120px]"></th>
            <td mat-cell *matCellDef="let s">
                <button mat-icon-button color="primary" (click)="openEditDialog(s)">
                    <mat-icon>edit</mat-icon>
                </button>
                <button mat-icon-button color="warn" (click)="deleteSynonym(s)">
                    <mat-icon>delete</mat-icon>
                </button>
            </td>
          </ng-container>

          <tr mat-header-row *matHeaderRowDef="displayedColumns; sticky: true"></tr>
          <tr mat-row *matRowDef="let row; columns: displayedColumns;" class="hover:bg-slate-800/30"></tr>
        </table>
        
        <div *ngIf="synonyms.length === 0" class="p-8 text-center text-gray-500">
            No synonyms defined.
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
export class SynonymsManagerComponent implements OnInit, OnChanges {
  @Input() datasourceId: string | null = null;

  synonyms: Synonym[] = [];
  loading = signal<boolean>(false);
  displayedColumns = ['term', 'target', 'actions'];

  // Cache for resolving names
  targetNameCache: Map<string, string> = new Map();
  // Keep reference to tables for dialog
  tables: any[] = [];

  constructor(private adminService: AdminService, private route: ActivatedRoute, private dialog: MatDialog) { }

  ngOnInit() {
    if (!this.datasourceId) {
      this.route.parent?.paramMap.subscribe(params => {
        const id = params.get('id');
        if (id) {
          this.datasourceId = id;
          this.loadData();
        }
      });
    } else {
      this.loadData();
    }
  }

  ngOnChanges(changes: SimpleChanges) {
    if (changes['datasourceId'] && this.datasourceId) this.loadData();
  }

  loadData() {
    if (!this.datasourceId) return;
    this.loading.set(true);

    this.adminService.getTables(this.datasourceId).subscribe(tables => {
      this.tables = tables; // Cache tables
      // Pre-fill cache with table and column names
      tables.forEach(t => {
        this.targetNameCache.set(t.id, t.physical_name);
        t.columns.forEach(c => this.targetNameCache.set(c.id, `${t.physical_name}.${c.name}`));
      });

      this.adminService.getSynonyms().subscribe(allSynonyms => {
        // Client-side filter: Only show synonyms where target_id is in our cache
        // (meaning it belongs to a table/column in this datasource)
        this.synonyms = allSynonyms.filter(s => this.targetNameCache.has(s.target_id));
        this.loading.set(false);
      });
    });
  }

  openAddDialog() {
    this.dialog.open(CreateSynonymDialogComponent, {
      width: '500px',
      data: { tables: this.tables }
    }).afterClosed().subscribe(result => {
      if (result) {
        this.adminService.createSynonymsBulk(result).subscribe(() => this.loadData());
      }
    });
  }

  openEditDialog(synonym: Synonym) {
    this.dialog.open(CreateSynonymDialogComponent, {
      width: '500px',
      data: { tables: this.tables, synonym: synonym }
    }).afterClosed().subscribe(result => {
      if (result) {
        this.adminService.updateSynonym(result.id, result).subscribe(() => this.loadData());
      }
    });
  }

  resolveTargetName(s: Synonym): string {
    return this.targetNameCache.get(s.target_id) || s.target_id;
  }

  deleteSynonym(s: Synonym) {
    if (confirm(`Delete synonym "${s.term}"?`)) {
      this.adminService.deleteSynonym(s.id).subscribe(() => this.loadData());
    }
  }
}
