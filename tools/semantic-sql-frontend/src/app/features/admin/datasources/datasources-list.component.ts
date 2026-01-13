import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { MatTableModule } from '@angular/material/table';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatMenuModule } from '@angular/material/menu';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatSnackBar } from '@angular/material/snack-bar';
import { AdminService } from '../../../core/services/admin.service';
import { Datasource } from '../../../core/models/admin.models';
import { CreateDatasourceDialogComponent } from './create-datasource-dialog.component';

@Component({
    selector: 'app-datasources-list',
    standalone: true,
    imports: [
        CommonModule,
        RouterModule,
        MatTableModule,
        MatButtonModule,
        MatIconModule,
        MatMenuModule,
        MatCheckboxModule,
        MatDialogModule
    ],
    templateUrl: './datasources-list.component.html',
    styles: [`
    table { width: 100%; }
    th.mat-header-cell { font-weight: bold; color: #4a5568; }
  `]
})
export class DatasourcesListComponent implements OnInit {
    datasources: Datasource[] = [];
    displayedColumns: string[] = ['name', 'engine', 'slug', 'actions'];

    constructor(
        private adminService: AdminService,
        private dialog: MatDialog,
        private snackBar: MatSnackBar
    ) { }

    ngOnInit() {
        this.loadDatasources();
    }

    loadDatasources() {
        this.adminService.getDatasources().subscribe(data => {
            this.datasources = data;
        });
    }

    openCreateDialog() {
        const dialogRef = this.dialog.open(CreateDatasourceDialogComponent, {
            width: '600px',
            panelClass: 'border-gray-800'
        });

        dialogRef.afterClosed().subscribe(result => {
            if (result) {
                this.adminService.createDatasource(result).subscribe({
                    next: (newDs) => {
                        this.snackBar.open('Datasource configured successfully', 'Dismiss', { duration: 3000 });
                        this.loadDatasources();
                    },
                    error: (err) => {
                        console.error('Error creating datasource', err);
                        this.snackBar.open('Error creating datasource', 'Dismiss', { duration: 3000 });
                    }
                });
            }
        });
    }

    refreshIndex(ds: Datasource) {
        this.adminService.refreshDatasourceIndex(ds.id).subscribe({
            next: (res) => {
                const count = res.updated_count || 0;
                this.snackBar.open(`Index refreshed: ${count} entities updated`, 'Dismiss', { duration: 3000 });
            },
            error: (err) => {
                this.snackBar.open('Error refreshing index', 'Dismiss', { duration: 3000 });
            }
        });
    }

    deleteDatasource(ds: Datasource) {
        if (confirm(`Are you sure you want to delete ${ds.name}?`)) {
            this.adminService.deleteDatasource(ds.id).subscribe(() => {
                this.loadDatasources();
                this.snackBar.open('Datasource deleted', 'Dismiss', { duration: 3000 });
            });
        }
    }
}
