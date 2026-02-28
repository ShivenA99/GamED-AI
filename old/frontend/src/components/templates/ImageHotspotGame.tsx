'use client'

import { useState } from 'react'
import Image from 'next/image'
import type { ImageHotspotQABlueprint } from '@/types/gameBlueprint'

export function ImageHotspotGame({ blueprint }: { blueprint: ImageHotspotQABlueprint }) {
  const [selectedHotspot, setSelectedHotspot] = useState<string | null>(null)
  const [answers, setAnswers] = useState<Record<string, string>>({})

  const currentTask = blueprint.tasks.find(t => t.hotspotId === selectedHotspot)

  return (
    <div id="gameRoot" className="flex flex-col gap-4 p-6">
      <h2 className="text-xl font-bold">{blueprint.title}</h2>
      <p className="text-gray-600">{blueprint.narrativeIntro}</p>
      
      <div id="imageContainer" className="relative w-full h-[500px] border rounded-lg">
        {blueprint.image.assetUrl && (
          <Image
            src={blueprint.image.assetUrl}
            alt={blueprint.title}
            fill
            style={{ objectFit: 'contain' }}
          />
        )}
        {blueprint.hotspots.map(hotspot => (
          <div
            key={hotspot.id}
            className="absolute cursor-pointer"
            style={{
              left: `${hotspot.x * 100}%`,
              top: `${hotspot.y * 100}%`,
              width: `${hotspot.radius * 100}%`,
              height: `${hotspot.radius * 100}%`,
            }}
            onClick={() => setSelectedHotspot(hotspot.id)}
          >
            <div className="w-full h-full border-2 border-red-500 rounded-full bg-red-500/20" />
          </div>
        ))}
      </div>
      
      {currentTask && (
        <div id="questionModal" className="p-4 border rounded bg-white">
          <p className="font-semibold">{currentTask.questionText}</p>
          {currentTask.options && (
            <div className="mt-2 space-y-2">
              {currentTask.options.map((option, idx) => (
                <button
                  key={idx}
                  className="block w-full p-2 text-left border rounded hover:bg-gray-50"
                  onClick={() => setAnswers({ ...answers, [currentTask.id]: option })}
                >
                  {option}
                </button>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

