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
                    {
                        path: 'playground/retrieval',
                        loadComponent: () => import('./features/playground/retrieval/retrieval-playground.component').then(m => m.RetrievalPlaygroundComponent)
                    },
                    {
                        path: 'playground/validator',
                        loadComponent: () => import('./features/playground/validator/value-validator.component').then(m => m.ValueValidatorComponent)
                    },
                    {
                        path: 'playground/paths',
                        loadComponent: () => import('./features/playground/paths/search-paths.component').then(m => m.SearchPathsComponent)
                    }
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
        ];
    }
}

export const routes: Routes = AppRoutes.getRoutes();
