'use client'

import type { SpotTheMistakeBlueprint } from '@/types/gameBlueprint'

export function SpotTheMistakeGame({ blueprint }: { blueprint: SpotTheMistakeBlueprint }) {
  return (
    <div id="gameRoot" className="flex flex-col gap-4 p-6">
      <h2 className="text-xl font-bold">{blueprint.title}</h2>
      <p className="text-gray-600">{blueprint.narrativeIntro}</p>
      <div id="contentArea" className="border rounded p-4">
        {blueprint.content.code && (
          <pre className="font-mono">{blueprint.content.code}</pre>
        )}
        {blueprint.content.text && (
          <p>{blueprint.content.text}</p>
        )}
        {blueprint.content.assetUrl && (
          <img src={blueprint.content.assetUrl} alt="Content" />
        )}
      </div>
    </div>
  )
}

