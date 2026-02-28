'use client'

import { useState, useEffect } from 'react'
import StateTracerCodeGame from '@/components/templates/StateTracerCodeGame'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'

// Blueprint data from API - use unknown since structure varies by template
// eslint-disable-next-line @typescript-eslint/no-explicit-any
type ExternalBlueprint = any  // External API data, cannot be strongly typed

interface BlueprintData {
  filename: string
  topology: string
  timestamp: string
  title: string
  tasks: number
  steps: number
  blueprint: ExternalBlueprint
}

export default function ComparePage() {
  const [blueprints, setBlueprints] = useState<BlueprintData[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedT0, setSelectedT0] = useState<BlueprintData | null>(null)
  const [selectedT1, setSelectedT1] = useState<BlueprintData | null>(null)
  const [viewMode, setViewMode] = useState<'side-by-side' | 'single'>('side-by-side')
  const [activeGame, setActiveGame] = useState<'T0' | 'T1'>('T0')

  useEffect(() => {
    fetch('/api/blueprints')
      .then((res) => res.json())
      .then((data) => {
        setBlueprints(data.blueprints || [])

        // Auto-select most recent T0 and T1
        const t0 = data.blueprints?.find((b: BlueprintData) => b.topology === 'T0')
        const t1 = data.blueprints?.find((b: BlueprintData) => b.topology === 'T1')
        if (t0) setSelectedT0(t0)
        if (t1) setSelectedT1(t1)

        setLoading(false)
      })
      .catch((err) => {
        if (process.env.NODE_ENV === 'development') {
          console.error('Error loading blueprints:', err)
        }
        setLoading(false)
      })
  }, [])

  if (loading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-center">
          <div className="w-16 h-16 border-4 border-primary border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <p className="text-muted-foreground">Loading blueprints...</p>
        </div>
      </div>
    )
  }

  if (blueprints.length === 0) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-center px-4">
          <p className="text-muted-foreground mb-4">No blueprints found.</p>
          <p className="text-muted-foreground text-sm">
            Run the pipeline tests to generate blueprints:
          </p>
          <code className="text-primary text-sm block mt-2 break-all">
            FORCE_TEMPLATE=STATE_TRACER_CODE python scripts/run_and_save_blueprint.py
          </code>
        </div>
      </div>
    )
  }

  const t0Blueprints = blueprints.filter((b) => b.topology === 'T0')
  const t1Blueprints = blueprints.filter((b) => b.topology === 'T1')

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <div className="bg-card border-b border-border px-4 md:px-6 py-4">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div>
            <h1 className="text-xl md:text-2xl font-bold text-foreground">T0 vs T1 Comparison</h1>
            <p className="text-muted-foreground text-sm mt-1">
              Compare STATE_TRACER_CODE games from different topologies
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2 sm:gap-4">
            {/* View mode toggle */}
            <div className="flex rounded-lg overflow-hidden border border-border">
              <Button
                variant={viewMode === 'side-by-side' ? 'default' : 'ghost'}
                size="sm"
                onClick={() => setViewMode('side-by-side')}
                className="rounded-none"
              >
                <span className="hidden sm:inline">Side by Side</span>
                <span className="sm:hidden">Split</span>
              </Button>
              <Button
                variant={viewMode === 'single' ? 'default' : 'ghost'}
                size="sm"
                onClick={() => setViewMode('single')}
                className="rounded-none"
              >
                Single
              </Button>
            </div>

            <Button variant="ghost" size="sm" asChild>
              <a href="/" className="flex items-center gap-1">
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
                </svg>
                Home
              </a>
            </Button>
          </div>
        </div>
      </div>

      {/* Blueprint selectors */}
      <div className="bg-muted/50 border-b border-border px-4 md:px-6 py-3">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-start sm:items-center gap-4 sm:gap-8">
          {/* T0 selector */}
          <div className="flex items-center gap-2 w-full sm:w-auto">
            <Badge variant="info" className="shrink-0">T0</Badge>
            <select
              value={selectedT0?.filename || ''}
              onChange={(e) => {
                const bp = blueprints.find((b) => b.filename === e.target.value)
                setSelectedT0(bp || null)
              }}
              className="flex-1 sm:flex-none bg-background text-foreground px-3 py-1.5 rounded-lg text-sm border border-input focus:ring-2 focus:ring-ring focus:outline-none"
              aria-label="Select T0 blueprint"
            >
              {t0Blueprints.map((bp) => (
                <option key={bp.filename} value={bp.filename}>
                  {bp.title} ({bp.tasks} tasks, {bp.steps} steps)
                </option>
              ))}
            </select>
          </div>

          {/* T1 selector */}
          <div className="flex items-center gap-2 w-full sm:w-auto">
            <Badge variant="success" className="shrink-0">T1</Badge>
            <select
              value={selectedT1?.filename || ''}
              onChange={(e) => {
                const bp = blueprints.find((b) => b.filename === e.target.value)
                setSelectedT1(bp || null)
              }}
              className="flex-1 sm:flex-none bg-background text-foreground px-3 py-1.5 rounded-lg text-sm border border-input focus:ring-2 focus:ring-ring focus:outline-none"
              aria-label="Select T1 blueprint"
            >
              {t1Blueprints.map((bp) => (
                <option key={bp.filename} value={bp.filename}>
                  {bp.title} ({bp.tasks} tasks, {bp.steps} steps)
                </option>
              ))}
            </select>
          </div>

          {viewMode === 'single' && (
            <div className="flex items-center gap-2 sm:ml-auto">
              <span className="text-sm text-muted-foreground">Active:</span>
              <Button
                variant={activeGame === 'T0' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setActiveGame('T0')}
                className={activeGame === 'T0' ? 'bg-blue-500 hover:bg-blue-600' : ''}
              >
                T0
              </Button>
              <Button
                variant={activeGame === 'T1' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setActiveGame('T1')}
                className={activeGame === 'T1' ? 'bg-green-500 hover:bg-green-600' : ''}
              >
                T1
              </Button>
            </div>
          )}
        </div>
      </div>

      {/* Games */}
      <div className="p-4 md:p-6">
        {viewMode === 'side-by-side' ? (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* T0 Game */}
            <div>
              <div className="flex items-center mb-4">
                <Badge variant="info" className="text-sm">
                  T0 - Sequential Baseline
                </Badge>
              </div>
              {selectedT0?.blueprint ? (
                <StateTracerCodeGame
                  blueprint={selectedT0.blueprint}
                  onComplete={() => {}}
                  sessionId="t0-compare"
                  theme="dark"
                />
              ) : (
                <div className="bg-muted rounded-lg p-8 text-center text-muted-foreground">
                  No T0 blueprint selected
                </div>
              )}
            </div>

            {/* T1 Game */}
            <div>
              <div className="flex items-center mb-4">
                <Badge variant="success" className="text-sm">
                  T1 - Sequential Validated
                </Badge>
              </div>
              {selectedT1?.blueprint ? (
                <StateTracerCodeGame
                  blueprint={selectedT1.blueprint}
                  onComplete={() => {}}
                  sessionId="t1-compare"
                  theme="dark"
                />
              ) : (
                <div className="bg-muted rounded-lg p-8 text-center text-muted-foreground">
                  No T1 blueprint selected
                </div>
              )}
            </div>
          </div>
        ) : (
          <div className="max-w-4xl mx-auto">
            {activeGame === 'T0' && selectedT0?.blueprint && (
              <>
                <div className="flex items-center mb-4">
                  <Badge variant="info" className="text-sm">
                    T0 - Sequential Baseline
                  </Badge>
                </div>
                <StateTracerCodeGame
                  blueprint={selectedT0.blueprint}
                  onComplete={() => {}}
                  sessionId="t0-single"
                  theme="dark"
                />
              </>
            )}
            {activeGame === 'T1' && selectedT1?.blueprint && (
              <>
                <div className="flex items-center mb-4">
                  <Badge variant="success" className="text-sm">
                    T1 - Sequential Validated
                  </Badge>
                </div>
                <StateTracerCodeGame
                  blueprint={selectedT1.blueprint}
                  onComplete={() => {}}
                  sessionId="t1-single"
                  theme="dark"
                />
              </>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
