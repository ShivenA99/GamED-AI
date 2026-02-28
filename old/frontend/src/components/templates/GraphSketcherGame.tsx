'use client'

import type { GraphSketcherBlueprint } from '@/types/gameBlueprint'

export function GraphSketcherGame({ blueprint }: { blueprint: GraphSketcherBlueprint }) {
  return (
    <div id="gameRoot" className="flex flex-col gap-4 p-6">
      <h2 className="text-xl font-bold">{blueprint.title}</h2>
      <p className="text-gray-600">{blueprint.narrativeIntro}</p>
      <div className="flex gap-4">
        <div id="toolsPanel" className="w-48 space-y-2">
          <button className="w-full p-2 border rounded">Add Node</button>
          <button className="w-full p-2 border rounded">Add Edge</button>
        </div>
        <div id="graphCanvas" className="flex-1 border rounded min-h-[400px] bg-gray-50">
          {/* Graph canvas implementation */}
        </div>
      </div>
    </div>
  )
}

