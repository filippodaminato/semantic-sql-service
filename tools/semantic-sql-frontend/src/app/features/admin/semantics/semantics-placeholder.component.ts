import { Component } from '@angular/core';

@Component({
    selector: 'app-semantics-placeholder',
    standalone: true,
    template: `
    <div class="container mx-auto p-6 text-center mt-20">
      <h1 class="text-3xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-pink-400 to-orange-400 mb-4">
        Semantic Layer
      </h1>
      <p class="text-gray-400 mb-8">Define metrics and synonyms.</p>
      <div class="inline-block p-4 border border-dashed border-gray-600 rounded text-gray-500">
        🚧 Component under construction
      </div>
    </div>
  `
})
export class SemanticsPlaceholderComponent { }
