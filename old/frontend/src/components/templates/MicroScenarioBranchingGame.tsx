'use client'

import { useState } from 'react'
import type { MicroScenarioBranchingBlueprint } from '@/types/gameBlueprint'

export function MicroScenarioBranchingGame({ blueprint }: { blueprint: MicroScenarioBranchingBlueprint }) {
  const [currentScenarioId, setCurrentScenarioId] = useState(blueprint.scenarios[0]?.id)

  const currentScenario = blueprint.scenarios.find(s => s.id === currentScenarioId)
  const availableBranches = blueprint.branches.filter(b => b.fromScenarioId === currentScenarioId)

  return (
    <div id="gameRoot" className="flex flex-col gap-4 p-6">
      <h2 className="text-xl font-bold">{blueprint.title}</h2>
      <p className="text-gray-600">{blueprint.narrativeIntro}</p>
      <div id="scenarioDisplay" className="border rounded p-6">
        {currentScenario && (
          <>
            <p className="mb-4">{currentScenario.text}</p>
            <div id="choicesPanel" className="space-y-2">
              {availableBranches.map(branch => (
                <button
                  key={branch.id}
                  className="w-full p-3 border rounded text-left hover:bg-gray-50"
                  onClick={() => setCurrentScenarioId(branch.toScenarioId)}
                >
                  {branch.choiceText}
                </button>
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  )
}

