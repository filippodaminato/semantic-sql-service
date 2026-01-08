import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, RouterModule } from '@angular/router';
import { MatTabsModule } from '@angular/material/tabs';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { AdminService } from '../../../core/services/admin.service';
import { Datasource } from '../../../core/models/admin.models';
// Components
// Components removed (lazy loaded via router now)

@Component({
    selector: 'app-datasource-detail',
    standalone: true,
    imports: [
        CommonModule, RouterModule,
        MatTabsModule, MatButtonModule, MatIconModule, MatProgressSpinnerModule
    ],
    template: `
    <div class="h-full flex flex-col bg-[#0a0e14]">
      <!-- Compact Header -->
      <div class="bg-[#141a23] border-b border-gray-800 px-4 py-2 flex justify-between items-center h-[60px] shrink-0">
         <div *ngIf="datasource()" class="flex items-center gap-4">
             <button mat-icon-button routerLink="/admin/datasources" class="text-gray-400">
                 <mat-icon>arrow_back</mat-icon>
             </button>
             
             <div class="flex flex-col">
                 <div class="flex items-center gap-2">
                     <h1 class="text-lg font-bold text-white leading-none">{{datasource()?.name}}</h1>
                     <span class="px-1.5 py-0.5 rounded bg-gray-800 text-gray-400 text-[10px] font-mono border border-gray-700 uppercase leading-none">
                        {{datasource()?.engine}}
                     </span>
                 </div>
                 <span class="text-gray-500 text-[10px] font-mono leading-none mt-1">{{datasource()?.slug || 'No slug'}}</span>
             </div>
         </div>
         
         <div *ngIf="loading()" class="h-8 w-32 animate-pulse bg-gray-800 rounded"></div>
         
         <div class="flex gap-2">
            <button mat-stroked-button color="primary" class="scale-90 origin-right" (click)="refreshIndex()" [disabled]="refreshing()">
                <mat-icon [class.animate-spin]="refreshing()">sync</mat-icon> 
                {{ refreshing() ? 'INDEXING...' : 'REFRESH INDEX' }}
            </button>
         </div>
      </div>

       <!-- Content -->
       <nav mat-tab-nav-bar [tabPanel]="tabPanel" class="tech-tabs border-b border-gray-800 bg-[#141a23] shrink-0">
          <a mat-tab-link routerLink="graph" routerLinkActive #rla1="routerLinkActive" [active]="rla1.isActive" class="!h-[40px] !px-4 !min-w-[auto] !text-sm">Datasource</a>
          <a mat-tab-link routerLink="tables" routerLinkActive #rla2="routerLinkActive" [active]="rla2.isActive" class="!h-[40px] !px-4 !min-w-[auto] !text-sm">Tables</a>
          <a mat-tab-link routerLink="relationships" routerLinkActive #rla3="routerLinkActive" [active]="rla3.isActive" class="!h-[40px] !px-4 !min-w-[auto] !text-sm">Relationships</a>
          <a mat-tab-link routerLink="metrics" routerLinkActive #rla4="routerLinkActive" [active]="rla4.isActive" class="!h-[40px] !px-4 !min-w-[auto] !text-sm">Metrics</a>
          <a mat-tab-link routerLink="synonyms" routerLinkActive #rla5="routerLinkActive" [active]="rla5.isActive" class="!h-[40px] !px-4 !min-w-[auto] !text-sm">Synonyms</a>
          <a mat-tab-link routerLink="learning" routerLinkActive #rla6="routerLinkActive" [active]="rla6.isActive" class="!h-[40px] !px-4 !min-w-[auto] !text-sm">Golden SQL</a>
       </nav>
       
       <div class="flex-1 overflow-hidden relative">
          <mat-tab-nav-panel #tabPanel class="h-full w-full">
            <router-outlet></router-outlet>
          </mat-tab-nav-panel>
       </div>
    </div>
  `,
    styles: [`
    ::ng-deep .tech-tabs .mat-mdc-tab-link-container {
      border-bottom: none;
      background: #141a23;
    }
    ::ng-deep .tech-tabs .mat-mdc-tab-link {
        color: #9ca3af !important; /* gray-400 */
        font-weight: 500;
        opacity: 0.8;
    }
    ::ng-deep .tech-tabs .mat-mdc-tab-link-active {
        color: #60a5fa !important; /* blue-400 */
        background: rgba(30, 58, 138, 0.1);
        opacity: 1;
    }
    ::ng-deep .tech-tabs .mat-mdc-tab-header-pagination {
        display: none !important; /* Hide pagination arrows if not needed, or style them */
    }
    ::ng-deep .tech-tabs .mat-mdc-tab-body-wrapper {
        height: 100%;
    }
  `]
})
export class DatasourceDetailComponent implements OnInit {
    id: string = '';
    datasource = signal<Datasource | null>(null);
    loading = signal<boolean>(true);
    refreshing = signal<boolean>(false);
    selectedTabIndex = signal<number>(0);

    constructor(
        private route: ActivatedRoute,
        private adminService: AdminService
    ) { }

    onGraphNodeSelected(tableId: string) {
        this.selectedTabIndex.set(1); // Switch to Tables tab
        // TODO: Pass tableId to TablesViewComponent to select it
        // For now, user sees the list and can click. 
        // Ideally we would set a query param or share state.
        console.log('Selected table from graph:', tableId);
    }

    ngOnInit() {
        this.route.params.subscribe(params => {
            this.id = params['id'];
            this.loadDatasource();
        });
    }

    loadDatasource() {
        this.loading.set(true);
        this.adminService.getDatasource(this.id).subscribe({
            next: (ds) => {
                this.datasource.set(ds);
                this.loading.set(false);
            },
            error: (err) => {
                console.error('Error loading datasource', err);
                this.loading.set(false);
            }
        });
    }

    refreshIndex() {
        if (!this.id) return;
        this.refreshing.set(true);
        this.adminService.refreshDatasourceIndex(this.id).subscribe({
            next: () => {
                this.refreshing.set(false);
                // Maybe show toast
            },
            error: (err) => {
                console.error('Index refresh failed', err);
                this.refreshing.set(false);
            }
        });
    }
}
