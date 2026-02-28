'use client'

import type { BeforeAfterTransformerBlueprint } from '@/types/gameBlueprint'

export function BeforeAfterTransformerGame({ blueprint }: { blueprint: BeforeAfterTransformerBlueprint }) {
  return (
    <div id="gameRoot" className="flex flex-col gap-4 p-6">
      <h2 className="text-xl font-bold">{blueprint.title}</h2>
      <p className="text-gray-600">{blueprint.narrativeIntro}</p>
      <div className="grid grid-cols-2 gap-4">
        <div id="beforePanel" className="border rounded p-4">
          <h3 className="font-semibold mb-2">Before</h3>
          {blueprint.beforeState.assetUrl && (
            <img src={blueprint.beforeState.assetUrl} alt="Before" />
          )}
        </div>
        <div id="afterPanel" className="border rounded p-4">
          <h3 className="font-semibold mb-2">After</h3>
          {blueprint.afterState.assetUrl && (
            <img src={blueprint.afterState.assetUrl} alt="After" />
          )}
        </div>
      </div>
      <div id="transformationsPanel" className="border rounded p-4">
        <h3 className="font-semibold mb-2">Transformations</h3>
        {blueprint.transformations.map(trans => (
          <div key={trans.id} className="p-2 border rounded mb-2">
            {trans.description}
          </div>
        ))}
      </div>
    </div>
  )
}

