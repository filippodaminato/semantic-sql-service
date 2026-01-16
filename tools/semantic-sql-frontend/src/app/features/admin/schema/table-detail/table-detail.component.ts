import { Component, OnInit, Input, OnChanges, SimpleChanges } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatTableModule } from '@angular/material/table';
import { MatSelectModule } from '@angular/material/select';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatTabsModule } from '@angular/material/tabs';
import { AdminService } from '../../../../core/services/admin.service';
import { Table, Column, ContextRule, NominalValue } from '../../../../core/models/admin.models';
import { ContextRulesDialogComponent } from './context-rules-dialog.component';
import { NominalValuesDialogComponent } from './nominal-values-dialog.component';

@Component({
  selector: 'app-add-column-dialog',
  standalone: true,
  imports: [CommonModule, FormsModule, MatFormFieldModule, MatInputModule, MatButtonModule, MatSlideToggleModule, MatDialogModule, MatSelectModule],
  template: `
    <h2 mat-dialog-title class="text-white">Add Column</h2>
    <mat-dialog-content class="mat-typography">
      <div class="flex flex-col gap-4 min-w-[400px]">
        <mat-form-field appearance="outline" class="w-full tech-input">
          <mat-label>Column Name (Physical)</mat-label>
          <input matInput [(ngModel)]="data.name" placeholder="e.g. user_id">
        </mat-form-field>

        <mat-form-field appearance="outline" class="w-full tech-input">
          <mat-label>Slug</mat-label>
          <input matInput [(ngModel)]="data.slug" placeholder="e.g. user-id">
        </mat-form-field>

        <mat-form-field appearance="outline" class="w-full tech-input">
          <mat-label>Data Type</mat-label>
          <input matInput [(ngModel)]="data.data_type" placeholder="e.g. VARCHAR(255), INT, JSONB">
        </mat-form-field>
        
        <div class="flex items-center gap-2 text-gray-300">
           <mat-slide-toggle [(ngModel)]="data.is_primary_key" color="primary">Primary Key</mat-slide-toggle>
        </div>
      </div>
    </mat-dialog-content>
    <mat-dialog-actions align="end">
      <button mat-button mat-dialog-close class="text-gray-400">CANCEL</button>
      <button mat-flat-button color="primary" [mat-dialog-close]="data" [disabled]="!data.name || !data.slug">ADD</button>
    </mat-dialog-actions>
  `
})
export class AddColumnDialogComponent {
  data = { name: '', slug: '', data_type: 'VARCHAR', is_primary_key: false };
}

@Component({
  selector: 'app-table-detail',
  standalone: true,
  imports: [
    CommonModule, FormsModule,
    MatFormFieldModule, MatInputModule, MatIconModule, MatButtonModule,
    MatTableModule, MatSelectModule, MatSlideToggleModule, MatTooltipModule
  ],
  template: `
    <div *ngIf="table" class="h-full flex flex-col p-6 max-w-7xl mx-auto w-full overflow-y-auto custom-scrollbar">
      
      <!-- Top Actions Bar -->
      <div class="flex justify-between items-center mb-6">
          <div>
            <h2 class="text-xl font-bold text-white tracking-tight flex items-center gap-2">
                <mat-icon class="text-blue-400">table_chart</mat-icon>
                {{table.physical_name}}
            </h2>
            <p class="text-gray-500 text-xs font-mono mt-1">SCHEMA CONFIGURATION</p>
          </div>
          <div class="flex gap-2">
            <button mat-stroked-button color="warn" (click)="deleteTable()">
                <mat-icon>delete</mat-icon> DELETE
            </button>
            <button mat-flat-button color="primary" (click)="saveTableMetadata()">
                <mat-icon>save</mat-icon> SAVE CHANGES
            </button>
          </div>
      </div>

      <!-- Main Form Grid -->
      <div class="grid grid-cols-12 gap-6 mb-8">
          
          <!-- Left Column: Identity & Context -->
          <div class="col-span-8 flex flex-col gap-4">
              <!-- Identity Card -->
              <div class="bg-[#141a23] border border-gray-800 rounded-lg p-5">
                  <h3 class="text-gray-400 text-xs font-bold uppercase tracking-wider mb-4 border-b border-gray-800 pb-2">Table Identity</h3>
                  <div class="grid grid-cols-2 gap-4">
                      
                      <div class="flex flex-col gap-1">
                          <label class="text-[10px] uppercase text-gray-500 font-bold ml-1">Physical Name</label>
                          <mat-form-field appearance="outline" class="w-full tech-input dense-input">
                              <input matInput [(ngModel)]="table.physical_name" placeholder="e.g. t_users">
                              <mat-icon matSuffix class="text-gray-600 text-sm">storage</mat-icon>
                          </mat-form-field>
                      </div>

                      <div class="flex flex-col gap-1">
                          <label class="text-[10px] uppercase text-gray-500 font-bold ml-1">Slug</label>
                          <mat-form-field appearance="outline" class="w-full tech-input dense-input">
                              <input matInput [(ngModel)]="table.slug" placeholder="e.g. t-users">
                              <mat-icon matSuffix class="text-gray-600 text-sm">link</mat-icon>
                          </mat-form-field>
                      </div>

                      <div class="flex flex-col gap-1">
                          <label class="text-[10px] uppercase text-gray-500 font-bold ml-1">Semantic Name</label>
                          <mat-form-field appearance="outline" class="w-full tech-input dense-input">
                              <input matInput [(ngModel)]="table.semantic_name" placeholder="Friendly Name">
                              <mat-icon matSuffix class="text-blue-400 text-sm">badge</mat-icon>
                          </mat-form-field>
                      </div>
                      
                      <div class="col-span-2 flex flex-col gap-1">
                          <label class="text-[10px] uppercase text-gray-500 font-bold ml-1">Description</label>
                          <mat-form-field appearance="outline" class="w-full tech-input">
                              <textarea matInput [(ngModel)]="table.description" placeholder="What does this table represent?" rows="2"></textarea>
                          </mat-form-field>
                      </div>

                  </div>
              </div>
          </div>

          <!-- Right Column: Technical Details -->
          <div class="col-span-4 flex flex-col gap-4">
               <div class="bg-[#141a23] border border-gray-800 rounded-lg p-5 h-full">
                  <h3 class="text-gray-400 text-xs font-bold uppercase tracking-wider mb-4 border-b border-gray-800 pb-2">Technical Context</h3>
                  
                  <div class="flex flex-col gap-1">
                      <label class="text-[10px] uppercase text-gray-500 font-bold ml-1">DDL / Schema Definition</label>
                      <mat-form-field appearance="outline" class="w-full tech-input">
                          <textarea matInput [(ngModel)]="table.ddl_context" placeholder="CREATE TABLE statement..." rows="8" class="font-mono text-[10px] leading-relaxed text-gray-400"></textarea>
                      </mat-form-field>
                  </div>
              </div>
          </div>
      </div>

      <!-- Content Sections -->
      <div class="flex flex-col gap-10">
        
        <!-- COLUMNS -->
        <div class="bg-[#141a23] rounded-lg border border-gray-800 flex flex-col">
            <div class="flex justify-between items-center p-4 border-b border-gray-800 bg-[#1e293b]/50">
                 <div>
                    <h4 class="text-white font-bold text-sm">Columns</h4>
                    <p class="text-gray-400 text-xs">Manage schema columns and data types.</p>
                 </div>
                 <button mat-stroked-button class="!border-gray-700 !text-gray-300" (click)="addColumn()">
                     <mat-icon>add</mat-icon> ADD COLUMN
                 </button>
            </div>
            
            <div class="overflow-auto max-h-[500px]">
                <table mat-table [dataSource]="table.columns" class="w-full bg-transparent">
                    <!-- Semantic Name Column -->
                    <ng-container matColumnDef="semantic_name">
                        <th mat-header-cell *matHeaderCellDef class="w-[200px]"> Semantic Name </th>
                        <td mat-cell *matCellDef="let col">
                            <input class="bg-transparent border-none text-gray-200 w-full focus:ring-1 focus:ring-blue-500 rounded px-1" 
                                [(ngModel)]="col.semantic_name" (blur)="updateColumn(col)">
                        </td>
                    </ng-container>

                    <!-- Physical Name Column -->
                    <ng-container matColumnDef="name">
                        <th mat-header-cell *matHeaderCellDef> Physical Column </th>
                        <td mat-cell *matCellDef="let col" class="text-gray-500 font-mono text-xs">
                            <input class="bg-transparent border-none text-gray-500 font-mono w-full focus:ring-1 focus:ring-blue-500 rounded px-1 text-xs" 
                                [(ngModel)]="col.name" (blur)="updateColumn(col)"> 
                        </td>
                    </ng-container>

                    <!-- Slug Column -->
                    <ng-container matColumnDef="slug">
                        <th mat-header-cell *matHeaderCellDef> Slug </th>
                        <td mat-cell *matCellDef="let col" class="text-gray-500 font-mono text-xs">
                           <input class="bg-transparent border-none text-gray-500 font-mono w-full focus:ring-1 focus:ring-blue-500 rounded px-1 text-xs" 
                                [(ngModel)]="col.slug" (blur)="updateColumn(col)" placeholder="Required" required>  
                        </td>
                    </ng-container>

                    <!-- Data Type Column -->
                    <ng-container matColumnDef="data_type">
                        <th mat-header-cell *matHeaderCellDef> Type </th>
                        <td mat-cell *matCellDef="let col" class="w-[150px]">
                             <input class="bg-transparent border-none text-blue-300 font-mono w-full focus:ring-1 focus:ring-blue-500 rounded px-1 text-xs" 
                                [(ngModel)]="col.data_type" (blur)="updateColumn(col)">
                        </td>
                    </ng-container>

                    <!-- Primary Key Column -->
                    <ng-container matColumnDef="is_primary_key">
                        <th mat-header-cell *matHeaderCellDef class="w-[80px] text-center"> PK </th>
                        <td mat-cell *matCellDef="let col" class="text-center">
                            <mat-slide-toggle [(ngModel)]="col.is_primary_key" color="primary" (change)="updateColumn(col)"></mat-slide-toggle>
                        </td>
                    </ng-container>

                    <!-- Description Column -->
                    <ng-container matColumnDef="description">
                        <th mat-header-cell *matHeaderCellDef> Description </th>
                        <td mat-cell *matCellDef="let col">
                        <input class="bg-transparent border-none text-gray-400 w-full focus:ring-1 focus:ring-blue-500 rounded px-1 text-sm italic" 
                                [(ngModel)]="col.description" (blur)="updateColumn(col)" placeholder="Add description...">
                        </td>
                    </ng-container>
                    
                    <!-- Context Note Column -->
                    <ng-container matColumnDef="context_note">
                        <th mat-header-cell *matHeaderCellDef> Context Note </th>
                        <td mat-cell *matCellDef="let col">
                        <input class="bg-transparent border-none text-yellow-500/80 w-full focus:ring-1 focus:ring-yellow-500 rounded px-1 text-sm" 
                                [(ngModel)]="col.context_note" (blur)="updateColumn(col)" placeholder="Specific context...">
                        </td>
                    </ng-container>

                    <!-- Actions Column -->
                    <ng-container matColumnDef="actions">
                        <th mat-header-cell *matHeaderCellDef class="w-[80px] text-right pr-4">Actions</th>
                        <td mat-cell *matCellDef="let col" class="text-right pr-2">
                            <button mat-icon-button color="warn" (click)="deleteColumn(col)" matTooltip="Delete Column">
                                <mat-icon class="text-red-900/50 hover:text-red-500 transition-colors scale-75">delete</mat-icon>
                            </button>
                        </td>
                    </ng-container>

                    <tr mat-header-row *matHeaderRowDef="displayedColumns; sticky: true"></tr>
                    <tr mat-row *matRowDef="let row; columns: displayedColumns;" class="hover:bg-slate-800/50 transition-colors"></tr>
                </table>
            </div>
        </div>

        <!-- CONTEXT RULES -->
        <div class="bg-[#141a23] rounded-lg border border-gray-800 flex flex-col">
            <div class="flex justify-between items-center p-3 border-b border-gray-800 bg-[#1e293b]/50">
                <div class="flex items-center gap-2">
                    <mat-icon class="text-yellow-500 text-sm">lightbulb</mat-icon>
                    <h4 class="text-white font-bold text-sm">Context Rules</h4>
                </div>
                <button mat-stroked-button class="!border-gray-700 !text-gray-300 scale-90" (click)="addContextRule()">
                    <mat-icon>add</mat-icon> ADD RULE
                </button>
            </div>
            <div class="overflow-auto max-h-[300px]">
                <table mat-table [dataSource]="table.context_rules || []" class="w-full bg-transparent">
                    <ng-container matColumnDef="column_name">
                        <th mat-header-cell *matHeaderCellDef class="w-[200px]"> Column </th>
                        <td mat-cell *matCellDef="let rule" class="text-blue-300 font-mono text-xs"> {{rule.column_name}} </td>
                    </ng-container>

                    <ng-container matColumnDef="rule_text">
                        <th mat-header-cell *matHeaderCellDef> Rule Definition </th>
                        <td mat-cell *matCellDef="let rule" class="text-gray-300 text-sm italic"> "{{rule.rule_text}}" </td>
                    </ng-container>

                    <ng-container matColumnDef="actions">
                        <th mat-header-cell *matHeaderCellDef class="w-[80px] text-right pr-4"></th>
                        <td mat-cell *matCellDef="let rule" class="text-right pr-2">
                            <button mat-icon-button color="warn" (click)="deleteRule(rule)">
                                <mat-icon class="scale-75">delete</mat-icon>
                            </button>
                        </td>
                    </ng-container>

                    <tr mat-header-row *matHeaderRowDef="contextRulesColumns; sticky: true"></tr>
                    <tr mat-row *matRowDef="let row; columns: contextRulesColumns;" class="hover:bg-slate-800/50 transition-colors"></tr>
                    
                    <tr class="mat-row" *matNoDataRow>
                        <td class="mat-cell p-8 text-center text-gray-500 italic" [attr.colspan]="contextRulesColumns.length">
                            No context rules defined. Add one using the button above.
                        </td>
                    </tr>
                </table>
            </div>
        </div>

        <!-- NOMINAL VALUES -->
        <div class="bg-[#141a23] rounded-lg border border-gray-800 flex flex-col">
            <div class="flex justify-between items-center p-3 border-b border-gray-800 bg-[#1e293b]/50">
                <div class="flex items-center gap-2">
                    <mat-icon class="text-green-500 text-sm">category</mat-icon>
                    <h4 class="text-white font-bold text-sm">Nominal Values</h4>
                </div>
                <button mat-stroked-button class="!border-gray-700 !text-gray-300 scale-90" (click)="addNominalValue()">
                     <mat-icon>add</mat-icon> ADD VALUE
                </button>
            </div>
             <div class="overflow-auto max-h-[300px]">
                <table mat-table [dataSource]="table.nominal_values || []" class="w-full bg-transparent">
                    <ng-container matColumnDef="column_name">
                        <th mat-header-cell *matHeaderCellDef class="w-[200px]"> Column </th>
                        <td mat-cell *matCellDef="let val" class="text-blue-300 font-mono text-xs"> {{val.column_name}} </td>
                    </ng-container>

                    <ng-container matColumnDef="raw">
                        <th mat-header-cell *matHeaderCellDef> Raw Value </th>
                        <td mat-cell *matCellDef="let val"> 
                            <span class="text-gray-400 font-mono text-sm bg-gray-900/30 rounded px-2 w-[1%] whitespace-nowrap">{{val.raw}}</span>
                        </td>
                    </ng-container>

                    <ng-container matColumnDef="label">
                        <th mat-header-cell *matHeaderCellDef> Semantic Label </th>
                        <td mat-cell *matCellDef="let val" class="text-gray-200 text-sm"> {{val.label}} </td>
                    </ng-container>

                    <ng-container matColumnDef="actions">
                        <th mat-header-cell *matHeaderCellDef class="w-[80px] text-right pr-4"></th>
                        <td mat-cell *matCellDef="let val" class="text-right pr-2">
                            <button mat-icon-button color="warn" (click)="deleteValue(val)">
                                <mat-icon class="scale-75">delete</mat-icon>
                            </button>
                        </td>
                    </ng-container>

                    <tr mat-header-row *matHeaderRowDef="nominalValuesColumns; sticky: true"></tr>
                    <tr mat-row *matRowDef="let row; columns: nominalValuesColumns;" class="hover:bg-slate-800/50 transition-colors"></tr>

                    <tr class="mat-row" *matNoDataRow>
                        <td class="mat-cell p-8 text-center text-gray-500 italic" [attr.colspan]="nominalValuesColumns.length">
                            No nominal values mapped. Add one using the button above.
                        </td>
                    </tr>
                </table>
            </div>
        </div>

      </div>
    
    <div *ngIf="!table" class="h-full flex flex-col items-center justify-center text-gray-500">
        <mat-icon class="text-6xl text-gray-700 mb-4 h-16 w-16">table_view</mat-icon>
        <p>Select a table to view details</p>
    </div>
  `,
  styles: [`
    // Custom table styles for "tech" look
    .mat-mdc-table {
        background: transparent;
    }
    .mat-mdc-header-row {
        background: #1e293b;
    }
    .mat-mdc-header-cell {
        color: #94a3b8;
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        border-bottom-color: #334155;
    }
    .mat-mdc-cell {
        border-bottom-color: #1e293b;
        color: #e2e8f0;
    }
    .mat-mdc-row:hover {
        background-color: rgba(30, 41, 59, 0.5);
    }
    .tech-input ::ng-deep .mat-mdc-form-field-subscript-wrapper {
        display: none;
    }
    // Make select smaller
    ::ng-deep .mat-mdc-select-value {
        color: #9ca3af !important; 
    }
  `]
})
export class TableDetailComponent implements OnChanges {
  @Input() table: Table | null = null;
  @Input() refreshCallback: (() => void) | null = null;

  displayedColumns = ['semantic_name', 'name', 'slug', 'data_type', 'is_primary_key', 'description', 'context_note', 'actions'];
  contextRulesColumns = ['column_name', 'rule_text', 'actions'];
  nominalValuesColumns = ['column_name', 'raw', 'label', 'actions'];

  constructor(private adminService: AdminService, private dialog: MatDialog) { }

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['table'] && this.table) {
      if (!this.table.columns || !this.table.context_rules || !this.table.nominal_values) {
        this.loadFullTableDetails(this.table.id);
      }
    }
  }

  loadFullTableDetails(id: string) {
    this.adminService.getTable(id).subscribe({
      next: (fullTable) => {
        this.table = fullTable;
      },
      error: (err) => console.error('Error loading full table details', err)
    });
  }

  saveTableMetadata() {
    if (!this.table) return;

    this.adminService.updateTable(this.table.id, {
      physical_name: this.table.physical_name,
      slug: this.table.slug, // Added slug update
      semantic_name: this.table.semantic_name,
      description: this.table.description,
      ddl_context: this.table.ddl_context
    }).subscribe({
      next: (res) => {
        console.log('Table metadata saved', res);
        // If a callback is provided (e.g. to refresh parent list), call it
        if (this.refreshCallback) this.refreshCallback();
      },
      error: (err) => {
        console.error('Error saving table metadata', err);
        alert('Failed to save table metadata');
      }
    });
  }

  updateColumn(col: Column) {
    this.adminService.updateColumn(col.id, {
      name: col.name, // Added name update
      slug: col.slug, // Added slug update
      semantic_name: col.semantic_name,
      description: col.description,
      context_note: col.context_note,
      is_primary_key: col.is_primary_key,
      data_type: col.data_type
    }).subscribe({
      next: (res) => console.log('Column updated', res),
      error: (err) => {
        console.error('Error updating column', err);
        alert('Failed to update column: ' + (err.error?.detail || err.message));
      }
    });
  }

  addColumn() {
    if (!this.table) return;

    this.dialog.open(AddColumnDialogComponent).afterClosed().subscribe(result => {
      if (result && this.table) {
        this.adminService.createColumn(this.table.id, result).subscribe({
          next: (newCol) => {
            if (this.table) {
              this.table.columns = [...this.table.columns, newCol];
            }
          },
          error: (err) => console.error('Error creating column', err)
        });
      }
    });
  }

  addContextRule() {
    if (!this.table) return;
    this.dialog.open(ContextRulesDialogComponent, {
      width: '600px',
      data: { columns: this.table.columns }
    }).afterClosed().subscribe(() => this.loadFullTableDetails(this.table!.id));
  }

  addNominalValue() {
    if (!this.table) return;
    this.dialog.open(NominalValuesDialogComponent, {
      width: '700px',
      data: { columns: this.table.columns }
    }).afterClosed().subscribe(() => this.loadFullTableDetails(this.table!.id));
  }

  deleteRule(rule: ContextRule) {
    if (confirm('Delete rule?')) {
      this.adminService.deleteContextRule(rule.id).subscribe(() => this.loadFullTableDetails(this.table!.id));
    }
  }

  deleteValue(val: NominalValue) {
    if (confirm(`Delete value "${val.raw}"?`)) {
      this.adminService.deleteValue(val.id).subscribe(() => this.loadFullTableDetails(this.table!.id));
    }
  }

  deleteColumn(col: Column) {
    if (confirm(`Are you sure you want to delete column "${col.name}"? This action cannot be undone.`)) {
      this.adminService.deleteColumn(col.id).subscribe({
        next: () => {
          if (this.table) {
            this.table.columns = this.table.columns.filter(c => c.id !== col.id);
          }
        },
        error: (err) => {
          console.error('Error deleting column', err);
          alert('Error deleting column: ' + (err.error?.detail || err.message));
        }
      });
    }
  }
  deleteTable() {
    if (!this.table) return;
    if (confirm(`Are you sure you want to delete table "${this.table.physical_name}"? This will delete all columns and relationships associated with it.`)) {
      this.adminService.deleteTable(this.table.id).subscribe({
        next: () => {
          // Refresh parent list
          if (this.refreshCallback) this.refreshCallback();
          this.table = null; // Clear selection
        },
        error: (err) => {
          console.error('Error deleting table', err);
          alert('Failed to delete table');
        }
      });
    }
  }
}
