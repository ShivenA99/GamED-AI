'use client'

import type { MatrixMatchBlueprint } from '@/types/gameBlueprint'

export function MatrixMatchGame({ blueprint }: { blueprint: MatrixMatchBlueprint }) {
  return (
    <div id="gameRoot" className="flex flex-col gap-4 p-6">
      <h2 className="text-xl font-bold">{blueprint.title}</h2>
      <p className="text-gray-600">{blueprint.narrativeIntro}</p>
      <div id="matrixGrid" className="border rounded overflow-hidden">
        <table className="w-full">
          <thead>
            <tr>
              <th className="border p-2"></th>
              {blueprint.columns.map(col => (
                <th key={col.id} className="border p-2">{col.label}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {blueprint.rows.map(row => (
              <tr key={row.id}>
                <td className="border p-2 font-semibold">{row.label}</td>
                {blueprint.columns.map(col => (
                  <td
                    key={col.id}
                    className="border p-2 cursor-pointer hover:bg-gray-50"
                  >
                    {/* Cell content */}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

