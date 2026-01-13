import { Component, Inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule, ReactiveFormsModule, FormBuilder, FormGroup, Validators } from '@angular/forms';
import { MatDialogRef, MAT_DIALOG_DATA, MatDialogModule } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatSelectModule } from '@angular/material/select';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { Table } from '../../../../core/models/admin.models';

@Component({
    selector: 'app-create-metric-dialog',
    standalone: true,
    imports: [
        CommonModule, ReactiveFormsModule, FormsModule,
        MatDialogModule, MatFormFieldModule, MatInputModule, MatButtonModule,
        MatSelectModule, MatIconModule, MatProgressSpinnerModule
    ],
    template: `
    <h2 mat-dialog-title class="text-white">{{data.metric ? 'Edit' : 'Create'}} Metric</h2>
    <mat-dialog-content class="mat-typography" [formGroup]="form">
      <div class="flex flex-col gap-4 min-w-[500px] py-2">
        
        <!-- Name & Description -->
        <mat-form-field appearance="outline" class="tech-input">
            <mat-label>Metric Name</mat-label>
            <input matInput formControlName="name" placeholder="e.g. Monthly Recurring Revenue">
            <mat-error *ngIf="form.get('name')?.hasError('required')">Name is required</mat-error>
        </mat-form-field>

        <mat-form-field appearance="outline" class="tech-input">
            <mat-label>Slug</mat-label>
            <input matInput formControlName="slug" placeholder="e.g. monthly-recurring-revenue">
            <mat-error *ngIf="form.get('slug')?.hasError('required')">Slug is required</mat-error>
        </mat-form-field>

        <mat-form-field appearance="outline" class="tech-input">
            <mat-label>Description</mat-label>
            <textarea matInput formControlName="description" rows="2" placeholder="Explain what this metric calculates"></textarea>
        </mat-form-field>

        <!-- Logic Section -->
        <div class="bg-[#0f131a] p-4 rounded border border-gray-800">
            <h3 class="text-xs font-bold text-gray-400 uppercase mb-2">Calculation Logic</h3>
            
            <mat-form-field appearance="outline" class="tech-input w-full">
                <mat-label>SQL Expression</mat-label>
                <textarea matInput formControlName="sql_expression" rows="3" class="font-mono text-xs text-blue-300" placeholder="e.g. SUM(amount)"></textarea>
                <mat-hint class="text-xs">Aggregate expression without FROM clause</mat-hint>
                <mat-error *ngIf="form.get('sql_expression')?.hasError('required')">SQL is required</mat-error>
            </mat-form-field>

            <mat-form-field appearance="outline" class="tech-input w-full mt-2">
                <mat-label>Filter Condition (WHERE)</mat-label>
                <input matInput formControlName="filter_condition" class="font-mono text-xs" placeholder="e.g. status = 'ACTIVE'">
                <mat-hint>Optional WHERE clause</mat-hint>
            </mat-form-field>
        </div>

        <!-- Dependencies -->
        <mat-form-field appearance="outline" class="tech-input">
            <mat-label>Required Tables</mat-label>
            <mat-select formControlName="required_table_ids" multiple>
                <mat-option *ngFor="let table of data.tables" [value]="table.id">
                    {{table.physical_name}} <span class="text-gray-500 text-xs">({{table.semantic_name || ''}})</span>
                </mat-option>
            </mat-select>
        </mat-form-field>

      </div>
    </mat-dialog-content>
    
    <mat-dialog-actions align="end" class="gap-2">
      <button mat-button mat-dialog-close class="text-gray-400">CANCEL</button>
      <button mat-flat-button color="primary" (click)="save()" [disabled]="form.invalid || loading()">
          <span *ngIf="!loading()">{{data.metric ? 'UPDATE' : 'CREATE'}}</span>
          <mat-spinner *ngIf="loading()" diameter="20" class="inline-block"></mat-spinner>
      </button>
    </mat-dialog-actions>
  `
})
export class CreateMetricDialogComponent {
    form: FormGroup;
    loading = signal<boolean>(false);

    constructor(
        private fb: FormBuilder,
        public dialogRef: MatDialogRef<CreateMetricDialogComponent>,
        @Inject(MAT_DIALOG_DATA) public data: { tables: Table[], metric?: any }
    ) {
        this.form = this.fb.group({
            name: [data.metric?.name || '', Validators.required],
            slug: [data.metric?.slug || '', Validators.required],
            description: [data.metric?.description || ''],
            sql_expression: [data.metric?.calculation_sql || '', Validators.required],
            filter_condition: [data.metric?.filter_condition || ''],
            required_table_ids: [data.metric?.required_table_ids || []]
        });
    }

    save() {
        if (this.form.valid) {
            this.dialogRef.close(this.form.value);
        }
    }
}
