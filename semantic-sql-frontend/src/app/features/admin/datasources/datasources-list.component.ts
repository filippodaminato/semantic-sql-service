import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { MatTableModule } from '@angular/material/table';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatMenuModule } from '@angular/material/menu';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { AdminService } from '../../../core/services/admin.service';
import { Datasource } from '../../../core/models/admin.models';

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
        private dialog: MatDialog
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
        // TODO: Implement create dialog
        console.log('Open create dialog');
    }

    refreshIndex(ds: Datasource) {
        this.adminService.refreshDatasourceIndex(ds.id).subscribe(res => {
            console.log('Index refreshed', res);
            // TODO: Show toast
        });
    }

    deleteDatasource(ds: Datasource) {
        if (confirm(`Are you sure you want to delete ${ds.name}?`)) {
            this.adminService.deleteDatasource(ds.id).subscribe(() => {
                this.loadDatasources();
            });
        }
    }
}
