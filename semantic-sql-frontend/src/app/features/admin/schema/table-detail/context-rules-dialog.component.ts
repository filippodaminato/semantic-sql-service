import { Component, Inject, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule, ReactiveFormsModule, FormBuilder, FormGroup, Validators } from '@angular/forms';
import { MatDialogRef, MAT_DIALOG_DATA, MatDialogModule } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatSelectModule } from '@angular/material/select';
import { MatListModule } from '@angular/material/list';
import { AdminService } from '../../../../core/services/admin.service';
import { ContextRule, Column } from '../../../../core/models/admin.models';

@Component({
    selector: 'app-context-rules-dialog',
    standalone: true,
    imports: [
        CommonModule, ReactiveFormsModule, FormsModule,
        MatDialogModule, MatFormFieldModule, MatInputModule, MatButtonModule,
        MatIconModule, MatSelectModule
    ],
    template: `
    <h2 mat-dialog-title class="text-white flex items-center gap-2">
        <mat-icon class="text-yellow-500">lightbulb</mat-icon>
        Add Context Rule
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
              <input matInput formControlName="slug" placeholder="e.g. rule-status-pending">
              <mat-error *ngIf="form.get('slug')?.hasError('required')">Required</mat-error>
          </mat-form-field>

          <mat-form-field appearance="outline" class="w-full tech-input">
              <mat-label>Rule Definition</mat-label>
              <textarea matInput formControlName="rule_text" rows="4" placeholder="e.g. Can only be NULL if status is 'PENDING'. Logic or constraint description."></textarea>
              <mat-error *ngIf="form.get('rule_text')?.hasError('required')">Rule text is required</mat-error>
          </mat-form-field>

      </div>

    </mat-dialog-content>
    
    <mat-dialog-actions align="end">
      <button mat-button mat-dialog-close class="text-gray-400">CANCEL</button>
      <button mat-flat-button color="primary" [disabled]="form.invalid || submitting()" (click)="addRule()">
          <mat-icon>add</mat-icon> ADD RULE
      </button>
    </mat-dialog-actions>
  `
})
export class ContextRulesDialogComponent {
    submitting = signal<boolean>(false);
    form: FormGroup;

    constructor(
        private adminService: AdminService,
        private fb: FormBuilder,
        public dialogRef: MatDialogRef<ContextRulesDialogComponent>,
        @Inject(MAT_DIALOG_DATA) public data: { columns: Column[], columnId?: string }
    ) {
        this.form = this.fb.group({
            column_id: [data.columnId || '', Validators.required],
            slug: ['', Validators.required],
            rule_text: ['', Validators.required]
        });
    }

    addRule() {
        if (this.form.invalid) return;

        this.submitting.set(true);
        const payload = {
            column_id: this.form.value.column_id,
            slug: this.form.value.slug,
            rule_text: this.form.value.rule_text
        };

        this.adminService.createContextRule(payload).subscribe({
            next: () => {
                this.submitting.set(false);
                this.dialogRef.close(true); // Return explicit success
            },
            error: (err) => {
                console.error(err);
                this.submitting.set(false);
            }
        });
    }
}
