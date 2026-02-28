'use client'

import { useState } from 'react'
import Image from 'next/image'
import type { LabelDiagramBlueprint } from '@/types/gameBlueprint'

interface LabelDiagramGameProps {
  blueprint: LabelDiagramBlueprint
}

export function LabelDiagramGame({ blueprint }: LabelDiagramGameProps) {
  const [placedLabels, setPlacedLabels] = useState<Record<string, string>>({})
  const [feedback, setFeedback] = useState<string>('')

  const handleLabelDrop = (labelId: string, zoneId: string) => {
    setPlacedLabels({ ...placedLabels, [zoneId]: labelId })
  }

  const handleSubmit = () => {
    // Validate placements
    const correct = blueprint.diagram.zones.every(zone => {
      const label = blueprint.labels.find(l => l.id === placedLabels[zone.id])
      return label?.isCorrect
    })
    setFeedback(correct ? 'Correct!' : 'Try again')
  }

  return (
    <div id="gameRoot" className="flex flex-col gap-4 p-6">
      <h2 id="questionText" className="text-xl font-bold">
        {blueprint.title}
      </h2>
      <p className="text-gray-600">{blueprint.narrativeIntro}</p>
      
      <div className="flex gap-4">
        <div id="diagramCanvas" className="relative w-[480px] h-[320px] border rounded-lg overflow-hidden bg-gray-50">
          {blueprint.diagram.assetUrl && (
            <Image
              src={blueprint.diagram.assetUrl}
              alt={blueprint.title}
              fill
              style={{ objectFit: 'contain' }}
            />
          )}
          {blueprint.diagram.zones.map(zone => (
            <div
              key={zone.id}
              className="absolute border-2 border-dashed border-blue-400 rounded-full"
              style={{
                left: `${zone.x * 100}%`,
                top: `${zone.y * 100}%`,
                width: `${zone.radius * 100}%`,
                height: `${zone.radius * 100}%`,
              }}
            />
          ))}
        </div>
        
        <div id="labelsPanel" className="flex flex-col gap-2">
          {blueprint.labels.map(label => (
            <div
              key={label.id}
              className="p-2 border rounded cursor-move bg-white"
              draggable
            >
              {label.text}
            </div>
          ))}
        </div>
      </div>
      
      <button id="submitBtn" onClick={handleSubmit} className="btn-primary">
        Check Answers
      </button>
      
      {feedback && (
        <div id="feedbackArea" className="mt-2 text-sm text-green-600">
          {feedback}
        </div>
      )}
    </div>
  )
}

