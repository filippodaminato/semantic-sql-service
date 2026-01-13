import { Component, Inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatDialogRef, MAT_DIALOG_DATA, MatDialogModule } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatSelectModule } from '@angular/material/select';
import { MatInputModule } from '@angular/material/input';
import { FormsModule } from '@angular/forms';
import { Table, Column } from '../../../../core/models/admin.models';

@Component({
    selector: 'app-create-relationship-dialog',
    standalone: true,
    imports: [
        CommonModule, MatDialogModule, MatButtonModule,
        MatFormFieldModule, MatSelectModule, MatInputModule, FormsModule
    ],
    template: `
    <h2 mat-dialog-title>{{data.relationship ? 'Edit' : 'Create'}} Relationship</h2>
    <mat-dialog-content>
      <div class="flex flex-col gap-4 py-4">
        
        <!-- Source -->
        <div class="grid grid-cols-2 gap-4">
            <mat-form-field appearance="outline">
                <mat-label>Source Table</mat-label>
                <mat-select [(ngModel)]="sourceTable" (selectionChange)="sourceColumn=null" [disabled]="!!data.relationship">
                    <mat-option *ngFor="let t of data.tables" [value]="t">{{t.physical_name}}</mat-option>
                </mat-select>
            </mat-form-field>

            <mat-form-field appearance="outline">
                <mat-label>Source Column</mat-label>
                <mat-select [(ngModel)]="sourceColumn" [disabled]="!sourceTable || !!data.relationship">
                    <mat-option *ngFor="let c of sourceTable?.columns" [value]="c">{{c.name}}</mat-option>
                </mat-select>
            </mat-form-field>
        </div>

        <!-- Relationship Type -->
        <mat-form-field appearance="outline">
            <mat-label>Relationship Type</mat-label>
            <mat-select [(ngModel)]="type">
                <mat-option value="ONE_TO_ONE">One-to-One</mat-option>
                <mat-option value="ONE_TO_MANY">One-to-Many</mat-option>
                <mat-option value="MANY_TO_MANY">Many-to-Many</mat-option>
            </mat-select>
        </mat-form-field>

        <!-- Target -->
         <div class="grid grid-cols-2 gap-4">
            <mat-form-field appearance="outline">
                <mat-label>Target Table</mat-label>
                <mat-select [(ngModel)]="targetTable" [disabled]="!!data.relationship">
                     <mat-option *ngFor="let t of data.tables" [value]="t">{{t.physical_name}}</mat-option>
                </mat-select>
            </mat-form-field>

            <mat-form-field appearance="outline">
                <mat-label>Target Column</mat-label>
                <mat-select [(ngModel)]="targetColumn" [disabled]="!targetTable || !!data.relationship">
                    <mat-option *ngFor="let c of targetTable?.columns" [value]="c">{{c.name}}</mat-option>
                </mat-select>
            </mat-form-field>
        </div>
        <!-- Description & Context -->
        <mat-form-field appearance="outline">
            <mat-label>Description</mat-label>
            <input matInput [(ngModel)]="description" placeholder="Why this relationship?">
        </mat-form-field>
        
        <mat-form-field appearance="outline">
            <mat-label>Context Note</mat-label>
            <textarea matInput [(ngModel)]="context_note" rows="2" placeholder="Technical nuances..."></textarea>
        </mat-form-field>
      </div>
    </mat-dialog-content>
    <mat-dialog-actions align="end">
      <button mat-button mat-dialog-close>CANCEL</button>
      <button mat-flat-button color="primary" [disabled]="!isValid()" (click)="save()">
        {{data.relationship ? 'UPDATE' : 'CREATE'}}
      </button>
    </mat-dialog-actions>
  `
})
export class CreateRelationshipDialogComponent {
    sourceTable: Table | null = null;
    sourceColumn: Column | null = null;
    targetTable: Table | null = null;
    targetColumn: Column | null = null;
    type: string = 'ONE_TO_MANY';
    description: string = '';
    context_note: string = '';

    constructor(
        public dialogRef: MatDialogRef<CreateRelationshipDialogComponent>,
        @Inject(MAT_DIALOG_DATA) public data: { tables: Table[], relationship?: any }
    ) {
        if (data.relationship) {
            this.type = data.relationship.relationship_type;
            this.description = data.relationship.description || '';
            this.context_note = data.relationship.context_note || '';

            // Find Source Table & Column
            const rel = data.relationship;
            // ... (rest of logic) ...
            if (rel.source_column_id) {
                this.sourceTable = this.data.tables.find(t => t.columns?.some(c => c.id === rel.source_column_id)) || null;
                if (this.sourceTable) {
                    this.sourceColumn = this.sourceTable.columns.find(c => c.id === rel.source_column_id) || null;
                }
            }

            // Find Target Table & Column
            if (rel.target_column_id) {
                this.targetTable = this.data.tables.find(t => t.columns?.some(c => c.id === rel.target_column_id)) || null;
                if (this.targetTable) {
                    this.targetColumn = this.targetTable.columns.find(c => c.id === rel.target_column_id) || null;
                }
            }
        }
    }

    isValid(): boolean {
        return !!(this.sourceColumn && this.targetColumn && this.type);
    }

    save() {
        this.dialogRef.close({
            source_column_id: this.sourceColumn!.id,
            target_column_id: this.targetColumn!.id,
            relationship_type: this.type,
            is_inferred: false,
            description: this.description,
            context_note: this.context_note
        });
    }
}
