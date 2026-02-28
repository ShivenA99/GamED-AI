'use client'

import type { ProbabilityLabBlueprint } from '@/types/gameBlueprint'

export function ProbabilityLabGame({ blueprint }: { blueprint: ProbabilityLabBlueprint }) {
  return (
    <div id="gameRoot" className="flex flex-col gap-4 p-6">
      <h2 className="text-xl font-bold">{blueprint.title}</h2>
      <p className="text-gray-600">{blueprint.narrativeIntro}</p>
      <div className="flex gap-4">
        <div id="experimentArea" className="flex-1 border rounded p-4">
          {blueprint.experiments.map(exp => (
            <div key={exp.id} className="mb-4">
              <h3 className="font-semibold">{exp.name}</h3>
              <p className="text-sm text-gray-600">{exp.description}</p>
            </div>
          ))}
        </div>
        <div id="controlsPanel" className="w-64 space-y-4">
          {blueprint.parameters.map(param => (
            <div key={param.id}>
              <label className="block mb-1">{param.label}</label>
              <input
                type="range"
                min={param.min}
                max={param.max}
                defaultValue={param.defaultValue as number}
                className="w-full"
              />
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

