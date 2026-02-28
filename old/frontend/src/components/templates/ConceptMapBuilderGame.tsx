'use client'

import type { ConceptMapBuilderBlueprint } from '@/types/gameBlueprint'

export function ConceptMapBuilderGame({ blueprint }: { blueprint: ConceptMapBuilderBlueprint }) {
  return (
    <div id="gameRoot" className="flex flex-col gap-4 p-6">
      <h2 className="text-xl font-bold">{blueprint.title}</h2>
      <p className="text-gray-600">{blueprint.narrativeIntro}</p>
      <div className="flex gap-4">
        <div id="conceptsPanel" className="w-64 space-y-2">
          {blueprint.concepts.map(concept => (
            <div key={concept.id} className="p-2 border rounded cursor-move">
              {concept.label}
            </div>
          ))}
        </div>
        <div id="mapCanvas" className="flex-1 border rounded min-h-[400px] bg-gray-50">
          {/* Concept map canvas */}
        </div>
      </div>
    </div>
  )
}

