'use client'

import type { MatchPairsBlueprint } from '@/types/gameBlueprint'

export function MatchPairsGame({ blueprint }: { blueprint: MatchPairsBlueprint }) {
  return (
    <div id="gameRoot" className="flex flex-col gap-4 p-6">
      <h2 className="text-xl font-bold">{blueprint.title}</h2>
      <p className="text-gray-600">{blueprint.narrativeIntro}</p>
      <div id="cardsContainer" className="grid grid-cols-4 gap-4">
        {blueprint.pairs.flatMap(pair => [
          <div key={`left-${pair.id}`} className="p-4 border rounded cursor-pointer hover:bg-gray-50">
            {pair.leftItem.text}
          </div>,
          <div key={`right-${pair.id}`} className="p-4 border rounded cursor-pointer hover:bg-gray-50">
            {pair.rightItem.text}
          </div>
        ])}
      </div>
    </div>
  )
}

