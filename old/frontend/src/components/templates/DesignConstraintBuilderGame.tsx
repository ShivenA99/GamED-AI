'use client'

import type { DesignConstraintBuilderBlueprint } from '@/types/gameBlueprint'

export function DesignConstraintBuilderGame({ blueprint }: { blueprint: DesignConstraintBuilderBlueprint }) {
  return (
    <div id="gameRoot" className="flex flex-col gap-4 p-6">
      <h2 className="text-xl font-bold">{blueprint.title}</h2>
      <p className="text-gray-600">{blueprint.narrativeIntro}</p>
      <div className="flex gap-4">
        <div id="constraintsPanel" className="w-64 space-y-2">
          <h3 className="font-semibold">Constraints</h3>
          {blueprint.constraints.map(constraint => (
            <div key={constraint.id} className="p-2 border rounded">
              {constraint.text}
            </div>
          ))}
        </div>
        <div id="designCanvas" className="flex-1 border rounded min-h-[400px] bg-gray-50">
          {/* Design canvas */}
        </div>
      </div>
    </div>
  )
}

