import { Component, Input, OnInit, OnChanges, SimpleChanges, signal } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { CommonModule } from '@angular/common';
import { MatSidenavModule } from '@angular/material/sidenav';
import { MatListModule } from '@angular/material/list';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { FormsModule } from '@angular/forms';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';

import { AdminService } from '../../../../core/services/admin.service';
import { Table } from '../../../../core/models/admin.models';
import { TableDetailComponent } from '../table-detail/table-detail.component';

@Component({
  selector: 'app-create-table-dialog',
  standalone: true,
  imports: [CommonModule, FormsModule, MatFormFieldModule, MatInputModule, MatButtonModule, MatDialogModule],
  template: `
    <h2 mat-dialog-title>Create Table</h2>
    <mat-dialog-content>
      <div class="flex flex-col gap-4 min-w-[350px] py-2">
        <mat-form-field appearance="outline">
            <mat-label>Physical Name</mat-label>
            <input matInput [(ngModel)]="data.physical_name" placeholder="e.g. t_users">
        </mat-form-field>
        <mat-form-field appearance="outline">
            <mat-label>Semantic Name</mat-label>
            <input matInput [(ngModel)]="data.semantic_name" placeholder="e.g. Users">
        </mat-form-field>
        <mat-form-field appearance="outline">
            <mat-label>Description</mat-label>
            <textarea matInput [(ngModel)]="data.description" rows="2"></textarea>
        </mat-form-field>
      </div>
    </mat-dialog-content>
    <mat-dialog-actions align="end">
      <button mat-button mat-dialog-close>CANCEL</button>
      <button mat-flat-button color="primary" [mat-dialog-close]="data" [disabled]="!data.physical_name || !data.semantic_name">CREATE</button>
    </mat-dialog-actions>
  `
})
export class CreateTableDialogComponent {
  data = { physical_name: '', semantic_name: '', description: '' };
}

@Component({
  selector: 'app-tables-view',
  standalone: true,
  imports: [
    CommonModule, FormsModule,
    MatSidenavModule, MatListModule, MatIconModule, MatButtonModule, MatProgressSpinnerModule, MatDialogModule,
    TableDetailComponent
  ],
  template: `
    <div class="h-full flex overflow-hidden bg-[#0a0e14]">
      <!-- Sidebar List of Tables -->
      <div class="w-80 flex flex-col border-r border-[#1f2937] bg-[#0f1218]">
        <!-- Sidebar Header -->
        <div class="p-4 border-b border-[#1f2937] bg-[#0f1218] flex flex-col gap-3 sticky top-0 z-10">
            <div class="flex justify-between items-center">
                <h3 class="text-xs font-bold uppercase text-blue-400 tracking-wider">Tables ({{tables().length}})</h3>
                <div class="flex">
                    <button mat-icon-button (click)="openCreateDialog()" matTooltip="Create Table" class="scale-90 text-gray-400 hover:text-white">
                        <mat-icon>add</mat-icon>
                    </button>
                    <button mat-icon-button (click)="loadTables()" [disabled]="loading()" class="scale-90 text-gray-400 hover:text-white">
                        <mat-icon [class.animate-spin]="loading()">refresh</mat-icon>
                    </button>
                </div>
            </div>
            <!-- Search Bar -->
             <div class="relative">
                <mat-icon class="absolute left-2 top-1.5 text-gray-600 text-sm h-4 w-4">search</mat-icon>
                <input type="text" placeholder="Search tables..." 
                       class="w-full bg-[#141a23] border border-[#2d3748] rounded px-8 py-1.5 text-xs text-gray-300 focus:border-blue-500 focus:outline-none transition-colors"
                       (input)="filterTables($event)">
             </div>
        </div>

        <!-- Sidebar Content -->
        <div class="flex-1 overflow-y-auto custom-scrollbar">
            <div *ngIf="loading() && tables().length === 0" class="flex justify-center p-8">
                <mat-spinner diameter="24"></mat-spinner>
            </div>

            <mat-nav-list class="pt-2 px-2 pb-4">
                <a mat-list-item *ngFor="let table of filteredTables()"
                (click)="selectedTable.set(table)"
                [class.active-table]="selectedTable()?.id === table.id"
                class="mb-1 rounded-md hover:bg-[#1a202c] transition-all h-auto py-2.5 border border-transparent group">
                <mat-icon matListItemIcon class="text-gray-600 group-hover:text-blue-400 text-sm transition-colors mt-0.5">table_chart</mat-icon>
                <div class="flex flex-col">
                    <span class="text-gray-300 text-sm font-medium leading-tight group-hover:text-white">{{table.physical_name}}</span>
                    <span class="text-gray-500 text-[10px] leading-tight mt-0.5 truncate">{{table.semantic_name || 'No semantic name'}}</span>
                </div>
                </a>
                <div *ngIf="!loading() && filteredTables().length === 0" class="text-center p-8 text-gray-600 text-xs">
                    No tables found.
                </div>
            </mat-nav-list>
        </div>
      </div>

      <!-- Main Content Area -->
      <div class="flex-1 overflow-hidden bg-[#0a0e14] relative flex flex-col">
         <app-table-detail *ngIf="selectedTable()" [table]="selectedTable()!" [refreshCallback]="refreshCallback" class="flex-1 flex flex-col overflow-hidden"></app-table-detail>

         <!-- Empty State -->
         <div *ngIf="!selectedTable()" class="flex-1 flex flex-col items-center justify-center text-gray-600">
            <div class="p-8 rounded-full bg-[#141a23] mb-4 border border-[#1f2937]">
                <mat-icon class="transform scale-150 text-gray-700 h-12 w-12">table_view</mat-icon>
            </div>
            <p class="text-sm font-medium">Select a table from the sidebar to view details</p>
         </div>
      </div>
    </div>
  `,
  styles: [`
    .active-table {
        background-color: rgba(30, 58, 138, 0.4) !important; /* blue-900/40 */
        border: 1px solid rgba(59, 130, 246, 0.3) !important;
    }
    .custom-scrollbar::-webkit-scrollbar {
        width: 6px;
    }
    .custom-scrollbar::-webkit-scrollbar-track {
        background: #0f1218;
    }
    .custom-scrollbar::-webkit-scrollbar-thumb {
        background: #2d3748;
        border-radius: 3px;
    }
    .custom-scrollbar::-webkit-scrollbar-thumb:hover {
        background: #4a5568;
    }
  `]
})
export class TablesViewComponent implements OnInit, OnChanges {
  @Input() datasourceId: string | null = null;

  tables = signal<Table[]>([]);
  loading = signal<boolean>(false);
  selectedTable = signal<Table | null>(null);

  // Filtering Logic
  filterQuery = signal<string>('');

  filteredTables() {
    const q = this.filterQuery().toLowerCase();
    if (!q) return this.tables();
    return this.tables().filter(t =>
      t.physical_name.toLowerCase().includes(q) ||
      (t.semantic_name && t.semantic_name.toLowerCase().includes(q))
    );
  }

  constructor(private adminService: AdminService, private dialog: MatDialog, private route: ActivatedRoute) { }

  refreshCallback = () => {
    this.loadTables();
  }

  filterTables(event: Event) {
    const input = event.target as HTMLInputElement;
    this.filterQuery.set(input.value);
  }

  ngOnInit() {
    // Check input or route param (input takes precedence if used as component, route param if used as page)
    if (!this.datasourceId) {
      this.route.parent?.paramMap.subscribe(params => {
        const id = params.get('id');
        if (id) {
          this.datasourceId = id;
          this.loadTables();
        }
      });
    } else {
      this.loadTables();
    }
  }

  ngOnChanges(changes: SimpleChanges) {
    if (changes['datasourceId'] && this.datasourceId) {
      this.loadTables();
    }
  }

  loadTables() {
    if (!this.datasourceId) return;

    this.loading.set(true);
    this.adminService.getTables(this.datasourceId).subscribe({
      next: (tables) => {
        this.tables.set(tables);
        this.loading.set(false);
        // Select first table by default if none selected
        if (tables.length > 0 && !this.selectedTable()) {
          this.selectedTable.set(tables[0]);
        }
      },
      error: (err) => {
        console.error('Error loading tables', err);
        this.loading.set(false);
      }
    });
  }

  openCreateDialog() {
    this.dialog.open(CreateTableDialogComponent, { width: '400px' })
      .afterClosed().subscribe((result: any) => {
        if (result && this.datasourceId) {
          this.adminService.createTable({
            datasource_id: this.datasourceId,
            ...result
          }).subscribe({
            next: (newTable) => {
              this.loadTables(); // Refresh list
              this.selectedTable.set(newTable); // Select new table
            },
            error: (err) => {
              console.error('Error creating table', err);
              alert('Error creating table');
            }
          });
        }
      });
  }
}
