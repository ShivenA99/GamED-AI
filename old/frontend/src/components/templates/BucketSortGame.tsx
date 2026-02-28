'use client'

import type { BucketSortBlueprint } from '@/types/gameBlueprint'

export function BucketSortGame({ blueprint }: { blueprint: BucketSortBlueprint }) {
  return (
    <div id="gameRoot" className="flex flex-col gap-4 p-6">
      <h2 className="text-xl font-bold">{blueprint.title}</h2>
      <p className="text-gray-600">{blueprint.narrativeIntro}</p>
      <div className="flex gap-4">
        <div id="itemsPanel" className="flex-1">
          <h3 className="font-semibold mb-2">Items</h3>
          {blueprint.items.map(item => (
            <div key={item.id} className="p-2 border rounded mb-2 cursor-move">
              {item.text}
            </div>
          ))}
        </div>
        <div id="bucketsContainer" className="flex-1 grid grid-cols-2 gap-4">
          {blueprint.buckets.map(bucket => (
            <div key={bucket.id} className="border-2 border-dashed p-4 rounded min-h-[200px]">
              <h3 className="font-semibold">{bucket.label}</h3>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

