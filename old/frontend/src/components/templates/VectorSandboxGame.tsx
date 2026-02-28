'use client'

import type { VectorSandboxBlueprint } from '@/types/gameBlueprint'

export function VectorSandboxGame({ blueprint }: { blueprint: VectorSandboxBlueprint }) {
  return (
    <div id="gameRoot" className="flex flex-col gap-4 p-6">
      <h2 className="text-xl font-bold">{blueprint.title}</h2>
      <p className="text-gray-600">{blueprint.narrativeIntro}</p>
      <div className="flex gap-4">
        <div id="controlsPanel" className="w-64 space-y-4">
          {blueprint.operations.map(op => (
            <button key={op.id} className="w-full p-2 border rounded">
              {op.label}
            </button>
          ))}
        </div>
        <div id="vectorCanvas" className="flex-1 border rounded min-h-[400px] bg-gray-50">
          {/* Vector canvas implementation */}
        </div>
      </div>
    </div>
  )
}

