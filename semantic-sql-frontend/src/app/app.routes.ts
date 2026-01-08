import { Routes } from '@angular/router';
import { MainLayoutComponent } from './core/layout/main-layout.component';

export class AppRoutes {
    static getRoutes(): Routes {
        return [
            {
                path: '',
                component: MainLayoutComponent,
                children: [
                    { path: '', redirectTo: 'admin/datasources', pathMatch: 'full' },
                    {
                        path: 'admin/datasources',
                        loadComponent: () => import('./features/admin/datasources/datasources-list.component').then(m => m.DatasourcesListComponent)
                    },
                ]
            },
            {
                path: 'admin/datasources/:id',
                loadComponent: () => import('./features/admin/datasource-detail/datasource-detail.component').then(m => m.DatasourceDetailComponent),
                children: [
                    { path: '', redirectTo: 'graph', pathMatch: 'full' },
                    { path: 'graph', loadComponent: () => import('./features/admin/schema/datasource-graph/datasource-graph.component').then(m => m.DatasourceGraphComponent) },
                    { path: 'tables', loadComponent: () => import('./features/admin/schema/tables-view/tables-view.component').then(m => m.TablesViewComponent) },
                    { path: 'relationships', loadComponent: () => import('./features/admin/schema/relationships-view/relationships-view.component').then(m => m.RelationshipsViewComponent) },
                    { path: 'metrics', loadComponent: () => import('./features/admin/semantics/metrics-manager/metrics-manager.component').then(m => m.MetricsManagerComponent) },
                    { path: 'synonyms', loadComponent: () => import('./features/admin/semantics/synonyms-manager/synonyms-manager.component').then(m => m.SynonymsManagerComponent) },
                    { path: 'learning', loadComponent: () => import('./features/admin/learning/golden-sql/golden-sql.component').then(m => m.GoldenSqlComponent) }
                ]
            },
            // Redirect old routes to datasources for now to avoid broken links if users bookmarked them
            { path: 'admin/schema', redirectTo: 'admin/datasources', pathMatch: 'full' },
            { path: 'admin/semantics', redirectTo: 'admin/datasources', pathMatch: 'full' },
            { path: 'admin/context', redirectTo: 'admin/datasources', pathMatch: 'full' },
            { path: 'admin/learning', redirectTo: 'admin/datasources', pathMatch: 'full' },
            {
                path: 'playground/search',
                loadComponent: () => import('./features/playground/search/omni-search.component').then(m => m.OmniSearchComponent)
            },
            {
                path: 'playground/graph',
                loadComponent: () => import('./features/playground/graph/graph-explorer.component').then(m => m.GraphExplorerComponent)
            },
            {
                path: 'playground/validator',
                loadComponent: () => import('./features/playground/validator/value-validator.component').then(m => m.ValueValidatorComponent)
            }
        ];
    }
}

export const routes: Routes = AppRoutes.getRoutes();
