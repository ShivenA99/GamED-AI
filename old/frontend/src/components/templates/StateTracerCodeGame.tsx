'use client'

import { useState } from 'react'
import type { StateTracerCodeBlueprint } from '@/types/gameBlueprint'

export function StateTracerCodeGame({ blueprint }: { blueprint: StateTracerCodeBlueprint }) {
  const [currentStep, setCurrentStep] = useState(0)

  return (
    <div id="gameRoot" className="flex flex-col gap-4 p-6">
      <h2 className="text-xl font-bold">{blueprint.title}</h2>
      <p className="text-gray-600">{blueprint.narrativeIntro}</p>
      <div className="flex gap-4">
        <div id="codeEditor" className="flex-1 border rounded p-4 bg-gray-900 text-white font-mono">
          <pre>{blueprint.code}</pre>
        </div>
        <div id="statePanel" className="w-64 border rounded p-4">
          <h3 className="font-semibold mb-2">Variables</h3>
          {blueprint.steps[currentStep] && (
            <div className="space-y-1 text-sm">
              {Object.entries(blueprint.steps[currentStep].expectedVariables).map(([key, value]) => (
                <div key={key}>
                  {key}: {String(value)}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
      <div id="stepControls" className="flex gap-2">
        <button onClick={() => setCurrentStep(Math.max(0, currentStep - 1))}>Previous</button>
        <button onClick={() => setCurrentStep(Math.min(blueprint.steps.length - 1, currentStep + 1))}>Next</button>
      </div>
    </div>
  )
}

