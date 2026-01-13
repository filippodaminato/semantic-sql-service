import { Component, Input, OnInit, OnChanges, SimpleChanges, signal } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { CommonModule } from '@angular/common';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatTableModule } from '@angular/material/table';
import { MatChipsModule } from '@angular/material/chips';
import { MatDialogModule, MatDialog } from '@angular/material/dialog';
import { MatSnackBar } from '@angular/material/snack-bar';
import { AdminService } from '../../../../core/services/admin.service';
import { GoldenSQL } from '../../../../core/models/admin.models';
import { GoldenSqlDialogComponent } from './golden-sql-dialog.component';

@Component({
  selector: 'app-golden-sql',
  standalone: true,
  imports: [
    CommonModule,
    MatButtonModule, MatIconModule, MatTableModule, MatChipsModule, MatDialogModule
  ],
  template: `
    <div class="h-full flex flex-col p-6 max-w-6xl mx-auto">
      <div class="flex justify-between items-center mb-6">
        <div>
           <h2 class="text-xl font-bold text-gray-200">Golden SQL</h2>
           <p class="text-gray-500 text-sm">Verified Question-SQL pairs for training the model</p>
        </div>
        
        <button mat-flat-button color="primary" [disabled]="loading()" (click)="openDialog()"> 
            <mat-icon>add_task</mat-icon> ADD EXAMPLE
        </button>
      </div>
      
      <div *ngIf="loading()" class="p-8 text-center text-gray-500">Loading...</div>

      <div *ngIf="!loading()" class="rounded-lg border border-gray-700 overflow-auto max-h-[calc(100vh-250px)] bg-[#141a23]">
        <table mat-table [dataSource]="goldenSqls" class="w-full bg-[#141a23]">
          
          <ng-container matColumnDef="prompt">
            <th mat-header-cell *matHeaderCellDef> User Question </th>
            <td mat-cell *matCellDef="let item" class="font-medium text-gray-200"> {{item.prompt_text}} </td>
          </ng-container>

          <ng-container matColumnDef="sql">
            <th mat-header-cell *matHeaderCellDef> SQL Query </th>
            <td mat-cell *matCellDef="let item" class="font-mono text-xs text-blue-300 py-3">
                <div class="max-w-md overflow-hidden text-ellipsis whitespace-nowrap" [title]="item.sql_query">{{item.sql_query}}</div>
            </td>
          </ng-container>
          
          <ng-container matColumnDef="complexity">
            <th mat-header-cell *matHeaderCellDef class="w-[100px] text-center"> Complexity </th>
            <td mat-cell *matCellDef="let item" class="text-center">
                 <span class="px-2 py-0.5 rounded text-xs border"
                     [class.border-green-800]="item.complexity_score < 3"
                     [class.bg-green-900]="item.complexity_score < 3"
                     [class.text-green-300]="item.complexity_score < 3"
                     [class.border-yellow-800]="item.complexity_score >= 3 && item.complexity_score < 7"
                     [class.bg-yellow-900]="item.complexity_score >= 3 && item.complexity_score < 7"
                     [class.text-yellow-300]="item.complexity_score >= 3 && item.complexity_score < 7"
                     [class.border-red-800]="item.complexity_score >= 7"
                     [class.bg-red-900]="item.complexity_score >= 7"
                     [class.text-red-300]="item.complexity_score >= 7">
                    {{item.complexity_score}}
                 </span>
            </td>
          </ng-container>

          <ng-container matColumnDef="actions">
            <th mat-header-cell *matHeaderCellDef class="w-[120px]"></th>
            <td mat-cell *matCellDef="let item">
              <button mat-icon-button color="primary" (click)="openDialog(item)">
                  <mat-icon>edit</mat-icon>
              </button>
              <button mat-icon-button color="warn" (click)="deleteItem(item)">
                  <mat-icon>delete</mat-icon>
              </button>
            </td>
          </ng-container>

          <tr mat-header-row *matHeaderRowDef="displayedColumns; sticky: true"></tr>
          <tr mat-row *matRowDef="let row; columns: displayedColumns;" class="hover:bg-slate-800/30"></tr>
        </table>
        
        <div *ngIf="goldenSqls.length === 0" class="p-8 text-center text-gray-500">
            No Golden SQL examples found for this datasource.
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
export class GoldenSqlComponent implements OnInit, OnChanges {
  @Input() datasourceId: string | null = null;

  goldenSqls: GoldenSQL[] = [];
  loading = signal<boolean>(false);
  displayedColumns = ['prompt', 'sql', 'complexity', 'actions'];

  constructor(
    private adminService: AdminService,
    private route: ActivatedRoute,
    private dialog: MatDialog,
    private snackBar: MatSnackBar
  ) { }

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

    this.adminService.getGoldenSQL(this.datasourceId).subscribe({
      next: (data) => {
        this.goldenSqls = data;
        this.loading.set(false);
      },
      error: (err) => {
        console.error(err);
        this.loading.set(false);
      }
    });
  }

  openDialog(item?: GoldenSQL) {
    if (!this.datasourceId) return;

    const dialogRef = this.dialog.open(GoldenSqlDialogComponent, {
      width: '600px',
      panelClass: 'border-gray-800',
      data: { datasourceId: this.datasourceId, item }
    });

    dialogRef.afterClosed().subscribe(result => {
      if (result) {
        if (item) {
          // Edit
          this.adminService.updateGoldenSQL(item.id, result).subscribe(() => {
            this.loadData();
            this.snackBar.open('Example updated', 'Dismiss', { duration: 3000 });
          });
        } else {
          // Create
          const newItem = { ...result, datasource_id: this.datasourceId! };
          this.adminService.createGoldenSQL(newItem).subscribe(() => {
            this.loadData();
            this.snackBar.open('Example created', 'Dismiss', { duration: 3000 });
          });
        }
      }
    });
  }

  deleteItem(item: GoldenSQL) {
    if (confirm('Are you sure you want to delete this example?')) {
      this.adminService.deleteGoldenSQL(item.id).subscribe({
        next: () => {
          this.loadData();
          this.snackBar.open('Example deleted', 'Dismiss', { duration: 3000 });
        },
        error: () => this.snackBar.open('Error deleting item', 'Dismiss', { duration: 3000 })
      });
    }
  }
}
