'use client'

import { useState } from 'react'
import type { SequenceBuilderBlueprint } from '@/types/gameBlueprint'

export function SequenceBuilderGame({ blueprint }: { blueprint: SequenceBuilderBlueprint }) {
  const [sequence, setSequence] = useState<string[]>([])

  const handleStepAdd = (stepId: string) => {
    if (!sequence.includes(stepId)) {
      setSequence([...sequence, stepId])
    }
  }

  const handleStepRemove = (stepId: string) => {
    setSequence(sequence.filter(id => id !== stepId))
  }

  return (
    <div id="gameRoot" className="flex flex-col gap-4 p-6">
      <h2 className="text-xl font-bold">{blueprint.title}</h2>
      <p className="text-gray-600">{blueprint.narrativeIntro}</p>
      
      <div className="flex gap-4">
        <div id="stepsContainer" className="flex-1">
          <h3 className="font-semibold mb-2">Available Steps</h3>
          <div className="space-y-2">
            {[...blueprint.steps, ...(blueprint.distractors || [])].map(step => (
              <div
                key={step.id}
                className="p-3 border rounded cursor-move bg-white"
                onClick={() => handleStepAdd(step.id)}
              >
                {step.text}
              </div>
            ))}
          </div>
        </div>
        
        <div id="dropZone" className="flex-1 border-2 border-dashed p-4 rounded">
          <h3 className="font-semibold mb-2">Sequence</h3>
          <div className="space-y-2">
            {sequence.map((stepId, idx) => {
              const step = [...blueprint.steps, ...(blueprint.distractors || [])].find(s => s.id === stepId)
              return step ? (
                <div
                  key={stepId}
                  className="p-3 border rounded bg-blue-50"
                  onClick={() => handleStepRemove(stepId)}
                >
                  {idx + 1}. {step.text}
                </div>
              ) : null
            })}
          </div>
        </div>
      </div>
    </div>
  )
}

