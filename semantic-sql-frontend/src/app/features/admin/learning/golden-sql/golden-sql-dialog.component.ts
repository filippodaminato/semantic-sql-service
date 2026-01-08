import { Component, Inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule, ReactiveFormsModule, FormBuilder, FormGroup, Validators } from '@angular/forms';
import { MatDialogModule, MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatIconModule } from '@angular/material/icon';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';
import { GoldenSQL } from '../../../../core/models/admin.models';

@Component({
    selector: 'app-golden-sql-dialog',
    standalone: true,
    imports: [
        CommonModule, FormsModule, ReactiveFormsModule,
        MatDialogModule, MatButtonModule, MatFormFieldModule, MatInputModule,
        MatSelectModule, MatIconModule, MatSlideToggleModule
    ],
    template: `
    <h2 mat-dialog-title class="!text-xl !font-bold text-white mb-2">
       {{isEdit ? 'Edit' : 'Add'}} Golden SQL Example
    </h2>
    
    <form [formGroup]="form" (ngSubmit)="onSubmit()">
        <div mat-dialog-content class="flex flex-col gap-4 !overflow-visible min-w-[500px]">
            
            <p class="text-gray-400 text-sm mb-2">
                Provide a natural language question and the corresponding validated SQL query.
            </p>

            <!-- Prompt -->
            <mat-form-field appearance="outline" class="w-full tech-input">
                <mat-label>User Question (Prompt)</mat-label>
                <textarea matInput formControlName="prompt_text" rows="2" placeholder="e.g. Total revenue by region..."></textarea>
                <mat-error *ngIf="form.get('prompt_text')?.hasError('required')">Required</mat-error>
            </mat-form-field>

            <!-- SQL -->
            <mat-form-field appearance="outline" class="w-full tech-input">
                <mat-label>SQL Query</mat-label>
                <textarea matInput formControlName="sql_query" rows="5" class="font-mono text-sm" placeholder="SELECT ..."></textarea>
                <mat-error *ngIf="form.get('sql_query')?.hasError('required')">Required</mat-error>
            </mat-form-field>

            <div class="grid grid-cols-2 gap-4">
                 <!-- Complexity -->
                 <mat-form-field appearance="outline" class="w-full tech-input">
                    <mat-label>Complexity Score (1-10)</mat-label>
                    <input matInput type="number" formControlName="complexity" min="1" max="10">
                </mat-form-field>

                 <!-- Verified -->
                <div class="flex items-center h-full pt-1">
                    <mat-slide-toggle formControlName="verified" color="primary">Verified Correct</mat-slide-toggle>
                </div>
            </div>

        </div>

        <div mat-dialog-actions align="end" class="!pt-4 !border-t border-gray-800">
            <button mat-button mat-dialog-close class="!text-gray-400">CANCEL</button>
            <button mat-flat-button color="primary" type="submit" [disabled]="form.invalid">
                {{isEdit ? 'SAVE CHANGES' : 'CREATE EXAMPLE'}}
            </button>
        </div>
    </form>
  `,
    styles: [`
    :host { display: block; }
    ::ng-deep .tech-input .mat-mdc-form-field-wrapper { padding-bottom: 0; }
  `]
})
export class GoldenSqlDialogComponent {
    form: FormGroup;
    isEdit = false;

    constructor(
        private fb: FormBuilder,
        private dialogRef: MatDialogRef<GoldenSqlDialogComponent>,
        @Inject(MAT_DIALOG_DATA) public data: { datasourceId: string, item?: GoldenSQL }
    ) {
        this.isEdit = !!data.item;

        this.form = this.fb.group({
            prompt_text: [data.item?.prompt_text || '', [Validators.required]],
            sql_query: [data.item?.sql_query || '', [Validators.required]],
            complexity: [data.item?.complexity_score || 1, [Validators.required, Validators.min(1), Validators.max(10)]],
            verified: [data.item?.verified ?? true]
        });
    }

    onSubmit() {
        if (this.form.valid) {
            this.dialogRef.close(this.form.value);
        }
    }
}
