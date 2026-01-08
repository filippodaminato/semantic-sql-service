import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { RetrievalService } from '../../../core/services/retrieval.service';
import { ValueValidationResponse } from '../../../core/models/retrieval.models';

@Component({
    selector: 'app-value-validator',
    standalone: true,
    imports: [
        CommonModule,
        FormsModule,
        MatInputModule,
        MatButtonModule,
        MatIconModule
    ],
    templateUrl: './value-validator.component.html'
})
export class ValueValidatorComponent {
    datasourceSlug = '';
    targetTable = '';
    targetColumn = '';
    proposedValuesInput = '';

    result: ValueValidationResponse | null = null;
    loading = false;

    constructor(private retrievalService: RetrievalService) { }

    validate() {
        if (!this.datasourceSlug || !this.targetTable || !this.targetColumn || !this.proposedValuesInput) return;

        this.loading = true;
        const values = this.proposedValuesInput.split(',').map(s => s.trim()).filter(s => s);

        this.retrievalService.validateValues({
            datasource_slug: this.datasourceSlug,
            target: { table: this.targetTable, column: this.targetColumn },
            proposed_values: values
        }).subscribe({
            next: (res) => {
                this.result = res;
                this.loading = false;
            },
            error: (err) => {
                console.error(err);
                this.loading = false;
            }
        });
    }
}
