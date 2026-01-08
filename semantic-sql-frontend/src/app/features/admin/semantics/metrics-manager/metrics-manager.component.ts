import { Component, Input, OnInit, OnChanges, SimpleChanges, signal } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { CommonModule } from '@angular/common';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatTableModule } from '@angular/material/table';
import { MatDialog } from '@angular/material/dialog';
import { MatTooltipModule } from '@angular/material/tooltip';
import { AdminService } from '../../../../core/services/admin.service';
import { Table, Metric } from '../../../../core/models/admin.models';
import { CreateMetricDialogComponent } from './create-metric-dialog.component';

@Component({
  selector: 'app-metrics-manager',
  standalone: true,
  imports: [
    CommonModule,
    MatButtonModule, MatIconModule, MatTableModule, MatTooltipModule
  ],
  template: `
    <div class="h-full flex flex-col p-6 max-w-6xl mx-auto">
      <div class="flex justify-between items-center mb-6">
        <div>
           <h2 class="text-xl font-bold text-gray-200">Metrics</h2>
           <p class="text-gray-500 text-sm">Define business metrics and KPI calculations</p>
        </div>
        
        <button mat-flat-button color="primary" [disabled]="loading()" (click)="openCreateDialog()"> 
            <mat-icon>add_chart</mat-icon> NEW METRIC
        </button>
      </div>
      
      <div *ngIf="loading()" class="p-8 text-center text-gray-500">
           Loading...
      </div>

      <div *ngIf="!loading()" class="rounded-lg border border-gray-700 overflow-auto max-h-[calc(100vh-250px)] bg-[#141a23]">
        <table mat-table [dataSource]="metrics" class="w-full bg-[#141a23]">
          
          <ng-container matColumnDef="name">
            <th mat-header-cell *matHeaderCellDef> Name </th>
            <td mat-cell *matCellDef="let m" class="font-bold text-gray-200"> {{m.name}} </td>
          </ng-container>

          <ng-container matColumnDef="sql">
            <th mat-header-cell *matHeaderCellDef> Calculation (SQL) </th>
            <td mat-cell *matCellDef="let m" class="font-mono text-xs text-blue-300"> 
                {{m.calculation_sql}} 
            </td>
          </ng-container>

          <ng-container matColumnDef="description">
            <th mat-header-cell *matHeaderCellDef> Description </th>
            <td mat-cell *matCellDef="let m" class="text-gray-400 text-sm"> {{m.description}} </td>
          </ng-container>

          <ng-container matColumnDef="actions">
            <th mat-header-cell *matHeaderCellDef class="w-[120px]"></th>
            <td mat-cell *matCellDef="let m">
                <button mat-icon-button color="primary" (click)="openCreateDialog(m)">
                    <mat-icon>edit</mat-icon>
                </button>
                <button mat-icon-button color="warn" (click)="deleteMetric(m)">
                    <mat-icon>delete</mat-icon>
                </button>
            </td>
          </ng-container>

          <tr mat-header-row *matHeaderRowDef="displayedColumns; sticky: true"></tr>
          <tr mat-row *matRowDef="let row; columns: displayedColumns;" class="hover:bg-slate-800/30"></tr>
        </table>
        
        <div *ngIf="metrics.length === 0" class="p-8 text-center text-gray-500">
            No metrics defined for this datasource.
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
export class MetricsManagerComponent implements OnInit, OnChanges {
  @Input() datasourceId: string | null = null;

  metrics: Metric[] = [];
  loading = signal<boolean>(false);
  displayedColumns = ['name', 'sql', 'description', 'actions'];

  tables: Table[] = [];

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

    // Load tables first (needed for metadata context)
    this.adminService.getTables(this.datasourceId).subscribe(tables => {
      this.tables = tables;
      this.loadMetrics(); // Then load metrics
    });
  }

  loadMetrics() {
    if (!this.datasourceId) return;
    this.adminService.getMetrics(this.datasourceId).subscribe(metrics => {
      this.metrics = metrics;
      this.loading.set(false);
    });
  }

  openCreateDialog(existingMetric: Metric | null = null) {
    this.dialog.open(CreateMetricDialogComponent, {
      width: '600px',
      data: { tables: this.tables, metric: existingMetric }
    }).afterClosed().subscribe(result => {
      if (result && this.datasourceId) {
        const payload = { ...result, datasource_id: this.datasourceId };

        if (existingMetric) {
          this.adminService.updateMetric(existingMetric.id, payload).subscribe(() => this.loadMetrics());
        } else {
          this.adminService.createMetric(payload).subscribe(() => this.loadMetrics());
        }
      }
    });
  }

  validateMetric(metric: Metric) {
    this.adminService.validateMetric(metric.id).subscribe(res => {
      if (res.is_valid) alert('Metric SQL is valid!');
      else alert('Metric SQL Invalid: ' + res.error_message);
    });
  }

  deleteMetric(metric: Metric) {
    if (confirm(`Delete metric "${metric.name}"?`)) {
      this.adminService.deleteMetric(metric.id).subscribe(() => this.loadMetrics());
    }
  }
}

