import { Component } from '@angular/core';

@Component({
    selector: 'app-context-placeholder',
    standalone: true,
    template: `
    <div class="container mx-auto p-6 text-center mt-20">
      <h1 class="text-3xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-green-400 to-teal-400 mb-4">
        Context Rules
      </h1>
      <p class="text-gray-400 mb-8">Manage business rules and context.</p>
      <div class="inline-block p-4 border border-dashed border-gray-600 rounded text-gray-500">
        🚧 Component under construction
      </div>
    </div>
  `
})
export class ContextPlaceholderComponent { }
