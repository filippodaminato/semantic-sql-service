import { Component, Inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule, ReactiveFormsModule, FormBuilder, FormGroup, Validators } from '@angular/forms';
import { MatDialogRef, MAT_DIALOG_DATA, MatDialogModule } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatSelectModule } from '@angular/material/select';
import { MatIconModule } from '@angular/material/icon';
import { MatChipsModule } from '@angular/material/chips';
import { LiveAnnouncer } from '@angular/cdk/a11y';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { Table } from '../../../../core/models/admin.models';

@Component({
    selector: 'app-create-synonym-dialog',
    standalone: true,
    imports: [
        CommonModule, ReactiveFormsModule, FormsModule,
        MatDialogModule, MatFormFieldModule, MatInputModule, MatButtonModule,
        MatSelectModule, MatIconModule, MatChipsModule, MatProgressSpinnerModule
    ],
    template: `
    <h2 mat-dialog-title class="text-white">{{data.synonym ? 'Edit Synonym' : 'Add Synonyms'}}</h2>
    <mat-dialog-content class="mat-typography" [formGroup]="form">
      <div class="flex flex-col gap-4 min-w-[500px] py-2">
        
        <!-- Target Type -->
        <mat-form-field appearance="outline" class="tech-input">
            <mat-label>Target Type</mat-label>
            <mat-select formControlName="target_type" (selectionChange)="onTypeChange()">
                <mat-option value="TABLE">Table</mat-option>
                <!-- <mat-option value="COLUMN">Column</mat-option> --> <!-- Temporarily disabled column until flat list or improved UI -->
                 <mat-option value="COLUMN">Column</mat-option>
            </mat-select>
        </mat-form-field>

        <!-- Target Entity -->
        <mat-form-field appearance="outline" class="tech-input">
            <mat-label>Target Entity</mat-label>
            <mat-select formControlName="target_id">
                <mat-option *ngFor="let entity of entities" [value]="entity.id">
                    {{entity.name}}
                </mat-option>
            </mat-select>
        </mat-form-field>

        <!-- Synonyms Input -->
        <mat-form-field appearance="outline" class="tech-input">
            <mat-label>{{data.synonym ? 'Synonym Term' : 'Synonyms (Comma separated)'}}</mat-label>
            <textarea matInput formControlName="terms_text" rows="3" [placeholder]="data.synonym ? 'e.g. Clients' : 'e.g. Clients, Buyers, Users'"></textarea>
            <mat-hint *ngIf="!data.synonym">Enter multiple terms separated by commas</mat-hint>
        </mat-form-field>

      </div>
    </mat-dialog-content>
    
    <mat-dialog-actions align="end" class="gap-2">
      <button mat-button mat-dialog-close class="text-gray-400">CANCEL</button>
      <button mat-flat-button color="primary" (click)="save()" [disabled]="form.invalid">
          {{data.synonym ? 'UPDATE' : 'ADD SYNONYMS'}}
      </button>
    </mat-dialog-actions>
  `
})
export class CreateSynonymDialogComponent {
    form: FormGroup;

    entities: { id: string, name: string }[] = [];

    constructor(
        private fb: FormBuilder,
        public dialogRef: MatDialogRef<CreateSynonymDialogComponent>,
        @Inject(MAT_DIALOG_DATA) public data: { tables: Table[], synonym?: any }
    ) {
        this.form = this.fb.group({
            target_type: [{ value: data.synonym?.target_type || 'TABLE', disabled: !!data.synonym }, Validators.required],
            target_id: [{ value: data.synonym?.target_id || '', disabled: !!data.synonym }, Validators.required],
            terms_text: [data.synonym?.term || '', Validators.required]
        });

        this.updateEntities();
    }

    onTypeChange() {
        this.form.get('target_id')?.reset();
        this.updateEntities();
    }

    updateEntities() {
        const type = this.form.get('target_type')?.value;

        if (type === 'TABLE') {
            this.entities = this.data.tables.map(t => ({ id: t.id, name: t.physical_name }));
        } else {
            // Flatten all columns
            let cols: { id: string, name: string }[] = [];
            this.data.tables.forEach(t => {
                t.columns.forEach(c => {
                    cols.push({ id: c.id, name: `${t.physical_name}.${c.name}` });
                });
            });
            this.entities = cols;
        }
    }

    save() {
        if (this.form.valid) {
            const formVal = this.form.getRawValue(); // Get disabled values too

            if (this.data.synonym) {
                // Edit Mode: Return single term string
                this.dialogRef.close({
                    id: this.data.synonym.id,
                    term: formVal.terms_text
                });
            } else {
                // Create Mode: Return bulk structure
                const terms = formVal.terms_text.split(',').map((t: string) => t.trim()).filter((t: string) => t.length > 0);
                this.dialogRef.close({
                    target_id: formVal.target_id,
                    target_type: formVal.target_type,
                    terms: terms
                });
            }
        }
    }
}
