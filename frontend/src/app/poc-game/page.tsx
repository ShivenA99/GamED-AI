'use client'

import { useState, useEffect } from 'react'
import InteractiveDiagramGame from '@/components/templates/InteractiveDiagramGame'
import { InteractiveDiagramBlueprint } from '@/components/templates/InteractiveDiagramGame/types'

export default function POCGamePage() {
  const [blueprint, setBlueprint] = useState<InteractiveDiagramBlueprint | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showDebug, setShowDebug] = useState(false)

  useEffect(() => {
    async function fetchBlueprint() {
      try {
        // Use Next.js API route (proxies to backend)
        const response = await fetch('/api/poc-game/blueprint')
        if (!response.ok) {
          throw new Error(`Failed to fetch blueprint: ${response.status}`)
        }
        const data = await response.json()

        // Image URL is already set to /api/poc-game/image by the API route
        setBlueprint(data)
      } catch (err) {
        console.error('Fetch error:', err)
        setError(err instanceof Error ? err.message : 'Failed to load game')
      } finally {
        setLoading(false)
      }
    }

    fetchBlueprint()
  }, [])

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-950 flex items-center justify-center">
        <div className="text-center">
          <div className="relative w-24 h-24 mx-auto mb-6">
            <div className="absolute inset-0 border-4 border-primary-200 rounded-full"></div>
            <div className="absolute inset-0 border-4 border-primary-500 rounded-full animate-spin border-t-transparent"></div>
          </div>
          <h2 className="text-2xl font-bold text-gray-200 mb-2">Loading POC Game</h2>
          <p className="text-gray-400">Fetching flower diagram data...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-950 flex items-center justify-center">
        <div className="text-center max-w-md">
          <div className="w-16 h-16 bg-red-900/50 rounded-full flex items-center justify-center mx-auto mb-4">
            <svg className="w-8 h-8 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </div>
          <h2 className="text-2xl font-bold text-gray-200 mb-2">Error Loading Game</h2>
          <p className="text-red-400 mb-4">{error}</p>
          <p className="text-gray-500 text-sm mb-4">
            Make sure the backend server is running: cd backend &amp;&amp; PYTHONPATH=. uvicorn app.main:app --port 8000
          </p>
          <button
            onClick={() => window.location.reload()}
            className="px-6 py-2 bg-primary-500 text-white rounded-lg hover:bg-primary-600"
          >
            Retry
          </button>
        </div>
      </div>
    )
  }

  if (!blueprint) {
    return (
      <div className="min-h-screen bg-gray-950 flex items-center justify-center">
        <p className="text-gray-400">No game data available</p>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-950 py-8">
      <div className="max-w-6xl mx-auto px-4">
        {/* Header */}
        <div className="mb-6 flex items-center justify-between">
          <a
            href="/"
            className="text-primary-400 hover:text-primary-300 flex items-center"
          >
            <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
            Back to Home
          </a>
          <button
            onClick={() => setShowDebug(!showDebug)}
            className="text-xs text-gray-500 hover:text-gray-400"
          >
            {showDebug ? 'Hide Debug' : 'Show Debug'}
          </button>
        </div>

        {/* POC Badge */}
        <div className="mb-6 p-4 bg-green-500/10 border border-green-500/30 rounded-lg">
          <div className="flex items-center gap-2">
            <span className="px-2 py-1 bg-green-500/20 text-green-400 text-xs font-semibold rounded">POC</span>
            <p className="text-green-400 text-sm">
              Proof of Concept - Parts of a Flower Label Diagram Game
            </p>
          </div>
          <p className="text-gray-500 text-xs mt-2">
            Uses Gemini-detected zones (12 flower parts) with CV2-cleaned diagram image
          </p>
        </div>

        {/* Debug Panel */}
        {showDebug && (
          <div className="mb-6 p-4 bg-gray-800/50 border border-gray-700 rounded-lg">
            <h3 className="text-sm font-semibold text-gray-300 mb-2">Blueprint Data</h3>
            <div className="grid grid-cols-3 gap-4 text-xs mb-4">
              <div>
                <span className="text-gray-500">Zones:</span>
                <span className="text-gray-300 ml-2">{blueprint.diagram.zones.length}</span>
              </div>
              <div>
                <span className="text-gray-500">Labels:</span>
                <span className="text-gray-300 ml-2">{blueprint.labels.length}</span>
              </div>
              <div>
                <span className="text-gray-500">Hints:</span>
                <span className="text-gray-300 ml-2">{blueprint.hints?.length || 0}</span>
              </div>
            </div>
            <details className="text-xs">
              <summary className="text-gray-400 cursor-pointer hover:text-gray-300">
                View Full Blueprint JSON
              </summary>
              <pre className="mt-2 p-2 bg-gray-900 rounded text-gray-400 overflow-auto max-h-60">
                {JSON.stringify(blueprint, null, 2)}
              </pre>
            </details>
          </div>
        )}

        {/* Game Component */}
        <div className="bg-gray-900/50 rounded-xl p-6 border border-gray-800">
          <InteractiveDiagramGame
            blueprint={blueprint}
            onComplete={() => {
              // Game completion handled by component
            }}
            sessionId="poc-flower-game"
          />
        </div>

        {/* Footer info */}
        <div className="mt-6 text-center text-gray-600 text-xs">
          <p>Pipeline: Gemini 3 Flash Zone Detection + CV2 Telea Inpainting</p>
          <p className="mt-1">12 zones detected: petal, sepal, stamen, anther, filament, pistil, stigma, style, ovary, ovule, receptacle, pedicel</p>
        </div>
      </div>
    </div>
  )
}
