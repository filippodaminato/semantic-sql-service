import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule, ReactiveFormsModule, FormBuilder, FormGroup, Validators } from '@angular/forms';
import { MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';

@Component({
    selector: 'app-create-datasource-dialog',
    standalone: true,
    imports: [
        CommonModule, FormsModule, ReactiveFormsModule,
        MatDialogModule, MatButtonModule, MatFormFieldModule, MatInputModule, MatSelectModule
    ],
    template: `
    <h2 mat-dialog-title class="!text-xl !font-bold text-white mb-2">Configure New Datasource</h2>
    
    <form [formGroup]="form" (ngSubmit)="onSubmit()">
        <div mat-dialog-content class="flex flex-col gap-4 !overflow-visible min-w-[500px]">
            
            <p class="text-gray-400 text-sm mb-2">
                Enter the details to configure a new semantic layer for your database.
            </p>

            <!-- Name -->
            <mat-form-field appearance="outline" class="w-full tech-input">
                <mat-label>Display Name</mat-label>
                <input matInput formControlName="name" placeholder="e.g. Sales Production DB">
                <mat-error *ngIf="form.get('name')?.hasError('required')">Required</mat-error>
            </mat-form-field>

            <!-- Slug -->
            <mat-form-field appearance="outline" class="w-full tech-input">
                <mat-label>Slug</mat-label>
                <input matInput formControlName="slug" placeholder="e.g. sales-production-db">
                <mat-error *ngIf="form.get('slug')?.hasError('required')">Required</mat-error>
            </mat-form-field>

            <!-- Engine -->
            <mat-form-field appearance="outline" class="w-full tech-input">
                <mat-label>Database Engine</mat-label>
                <mat-select formControlName="engine">
                    <mat-option value="postgres">PostgreSQL</mat-option>
                    <mat-option value="bigquery">BigQuery</mat-option>
                    <mat-option value="snowflake">Snowflake</mat-option>
                    <mat-option value="mysql">MySQL</mat-option>
                    <mat-option value="tsql">T-SQL (SQL Server)</mat-option>
                </mat-select>
                <mat-error *ngIf="form.get('engine')?.hasError('required')">Required</mat-error>
            </mat-form-field>

            <!-- Description -->
            <mat-form-field appearance="outline" class="w-full tech-input">
                <mat-label>Description (Optional)</mat-label>
                <textarea matInput formControlName="description" rows="2" placeholder="Brief context about this data..."></textarea>
            </mat-form-field>

            <!-- Context Signature -->
            <mat-form-field appearance="outline" class="w-full tech-input">
                <mat-label>Context Signature (Optional)</mat-label>
                <textarea matInput formControlName="context_signature" rows="2" placeholder="Keywords, key metrics, domain context..."></textarea>
            </mat-form-field>

        </div>

        <div mat-dialog-actions align="end" class="!pt-6 !border-t border-gray-800">
            <button mat-button mat-dialog-close class="!text-gray-400">CANCEL</button>
            <button mat-flat-button color="primary" type="submit" [disabled]="form.invalid">
                CREATE CONFIGURATION
            </button>
        </div>
    </form>
  `,
    styles: [`
    :host { display: block; }
    ::ng-deep .tech-input .mat-mdc-form-field-wrapper { padding-bottom: 0; }
  `]
})
export class CreateDatasourceDialogComponent {
    form: FormGroup;

    constructor(
        private fb: FormBuilder,
        private dialogRef: MatDialogRef<CreateDatasourceDialogComponent>
    ) {
        this.form = this.fb.group({
            name: ['', [Validators.required]],
            slug: ['', [Validators.required]],
            engine: ['postgres', [Validators.required]],
            description: [''],
            context_signature: ['']
        });
    }

    onSubmit() {
        if (this.form.valid) {
            this.dialogRef.close(this.form.value);
        }
    }
}
