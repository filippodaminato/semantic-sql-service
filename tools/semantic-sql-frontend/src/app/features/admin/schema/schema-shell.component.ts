import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatTabsModule } from '@angular/material/tabs';
import { TablesViewComponent } from './tables-view/tables-view.component';
import { RelationshipsViewComponent } from './relationships-view/relationships-view.component';

@Component({
    selector: 'app-schema-shell',
    standalone: true,
    imports: [
        CommonModule,
        MatTabsModule,
        TablesViewComponent,
        RelationshipsViewComponent
    ],
    template: `
    <div class="h-full flex flex-col">
      <div class="bg-[#141a23] border-b border-gray-700 px-6 pt-4">
        <h1 class="text-2xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-purple-400 to-blue-400 mb-4">
          Schema Management
        </h1>
        
        <mat-tab-group animationDuration="0ms" class="tech-tabs">
          <mat-tab label="Tables & Columns">
            <ng-template matTabContent>
              <app-tables-view></app-tables-view>
            </ng-template>
          </mat-tab>
          <mat-tab label="Relationships">
             <ng-template matTabContent>
               <app-relationships-view></app-relationships-view>
             </ng-template>
          </mat-tab>
        </mat-tab-group>
      </div>
      
      <!-- Content Area filled by tabs -->
      <div class="flex-1 overflow-hidden bg-[#0a0e14]">
         <!-- The tab content is projected here by mat-tab-group -->
      </div>
    </div>
  `,
    styles: [`
    ::ng-deep .tech-tabs .mat-mdc-tab-link-container {
      border-bottom: none;
    }
  `]
})
export class SchemaShellComponent { }
