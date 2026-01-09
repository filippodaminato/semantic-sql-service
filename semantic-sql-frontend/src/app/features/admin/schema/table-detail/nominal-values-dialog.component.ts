import { Component, Inject, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule, ReactiveFormsModule, FormBuilder, FormGroup, Validators } from '@angular/forms';
import { MatDialogRef, MAT_DIALOG_DATA, MatDialogModule } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatSelectModule } from '@angular/material/select';
import { MatTableModule } from '@angular/material/table';
import { AdminService } from '../../../../core/services/admin.service';
import { NominalValue, Column } from '../../../../core/models/admin.models';

@Component({
    selector: 'app-nominal-values-dialog',
    standalone: true,
    imports: [
        CommonModule, ReactiveFormsModule, FormsModule,
        MatDialogModule, MatFormFieldModule, MatInputModule, MatButtonModule,
        MatIconModule, MatSelectModule
    ],
    template: `
    <h2 mat-dialog-title class="text-white flex items-center gap-2">
        <mat-icon class="text-green-400">category</mat-icon>
        Add Nominal Value Mapping
    </h2>
    
    <mat-dialog-content class="mat-typography min-w-[500px]">
      
      <div class="bg-[#0f131a] p-4 rounded border border-gray-800 flex flex-col gap-4" [formGroup]="form">
          
          <mat-form-field appearance="outline" class="w-full tech-input">
              <mat-label>Target Column</mat-label>
              <mat-select formControlName="column_id">
                  <mat-option *ngFor="let col of data.columns" [value]="col.id">
                      {{col.name}} <span class="text-gray-500 text-xs" *ngIf="col.semantic_name">({{col.semantic_name}})</span>
                  </mat-option>
              </mat-select>
              <mat-error *ngIf="form.get('column_id')?.hasError('required')">Column is required</mat-error>
          </mat-form-field>

          <mat-form-field appearance="outline" class="w-full tech-input">
              <mat-label>Slug</mat-label>
              <input matInput formControlName="slug" placeholder="e.g. val-status-active">
              <mat-error *ngIf="form.get('slug')?.hasError('required')">Required</mat-error>
          </mat-form-field>

          <div class="flex gap-4">
            <mat-form-field appearance="outline" class="w-full tech-input">
                <mat-label>Raw Value</mat-label>
                <input matInput formControlName="raw" placeholder="e.g. 1">
                <mat-error *ngIf="form.get('raw')?.hasError('required')">Required</mat-error>
            </mat-form-field>

            <mat-form-field appearance="outline" class="w-full tech-input">
                <mat-label>Semantic Label</mat-label>
                <input matInput formControlName="label" placeholder="e.g. Active">
                <mat-error *ngIf="form.get('label')?.hasError('required')">Required</mat-error>
            </mat-form-field>
          </div>
          
      </div>

    </mat-dialog-content>
    
    <mat-dialog-actions align="end">
      <button mat-button mat-dialog-close class="text-gray-400">CANCEL</button>
      <button mat-flat-button color="primary" [disabled]="form.invalid || submitting()" (click)="addValue()">
          <mat-icon>add</mat-icon> ADD MAPPING
      </button>
    </mat-dialog-actions>
  `
})
export class NominalValuesDialogComponent {
    submitting = signal<boolean>(false);
    form: FormGroup;

    constructor(
        private adminService: AdminService,
        private fb: FormBuilder,
        public dialogRef: MatDialogRef<NominalValuesDialogComponent>,
        @Inject(MAT_DIALOG_DATA) public data: { columns: Column[], columnId?: string }
    ) {
        this.form = this.fb.group({
            column_id: [data.columnId || '', Validators.required],
            slug: ['', Validators.required],
            raw: ['', Validators.required],
            label: ['', Validators.required]
        });
    }

    addValue() {
        if (this.form.invalid) return;

        this.submitting.set(true);
        const payload = {
            slug: this.form.value.slug,
            raw: this.form.value.raw,
            label: this.form.value.label
        };

        this.adminService.addManualValue(this.form.value.column_id, payload).subscribe({
            next: () => {
                this.submitting.set(false);
                this.dialogRef.close(true);
            },
            error: (err) => {
                console.error(err);
                this.submitting.set(false);
            }
        });
    }
}
