'use client'

import type { GeometryBuilderBlueprint } from '@/types/gameBlueprint'

export function GeometryBuilderGame({ blueprint }: { blueprint: GeometryBuilderBlueprint }) {
  return (
    <div id="gameRoot" className="flex flex-col gap-4 p-6">
      <h2 className="text-xl font-bold">{blueprint.title}</h2>
      <p className="text-gray-600">{blueprint.narrativeIntro}</p>
      <div className="flex gap-4">
        <div id="toolsPanel" className="w-48 space-y-2">
          {blueprint.tools.map(tool => (
            <button key={tool.id} className="w-full p-2 border rounded">
              {tool.label}
            </button>
          ))}
        </div>
        <div id="geometryCanvas" className="flex-1 border rounded min-h-[400px] bg-gray-50">
          {/* Geometry canvas */}
        </div>
      </div>
    </div>
  )
}

