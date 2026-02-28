'use client'

import type { TimelineOrderBlueprint } from '@/types/gameBlueprint'

export function TimelineOrderGame({ blueprint }: { blueprint: TimelineOrderBlueprint }) {
  return (
    <div id="gameRoot" className="flex flex-col gap-4 p-6">
      <h2 className="text-xl font-bold">{blueprint.title}</h2>
      <p className="text-gray-600">{blueprint.narrativeIntro}</p>
      <div id="timelineContainer" className="border-t-2 border-gray-300 relative h-32">
        {/* Timeline implementation */}
      </div>
    </div>
  )
}

