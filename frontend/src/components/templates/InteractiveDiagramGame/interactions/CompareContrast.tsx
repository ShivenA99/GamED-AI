'use client'

import React, { useState, useCallback } from 'react'
import type { MechanicAction, ActionResult } from '../types'

/**
 * CompareContrast - Side-by-side comparison interaction component
 *
 * Users identify similarities and differences between two diagrams.
 * Supports categorization of zones into similar/different/unique categories.
 */

export interface ComparableDiagram {
  id: string
  name: string
  imageUrl: string
  zones: CompareZone[]
}

export interface CompareZone {
  id: string
  label: string
  x: number
  y: number
  width: number
  height: number
  category?: 'similar' | 'different' | 'unique_a' | 'unique_b'
}

export interface CompareContrastProps {
  diagramA: ComparableDiagram
  diagramB: ComparableDiagram
  expectedCategories: Record<string, 'similar' | 'different' | 'unique_a' | 'unique_b'>
  highlightMatching?: boolean
  instructions?: string
  // Store integration props (Fix 1.7h) — optional for standalone use
  storeProgress?: { categorizations: Record<string, string>; isSubmitted: boolean; correctCount: number; totalCount: number } | null
  /** V4 unified action dispatch */
  onAction?: (action: MechanicAction) => ActionResult | null
}

export interface CompareResult {
  isCorrect: boolean
  score: number
  maxScore: number
  categorizations: Record<string, string>
  correctCount: number
  totalCount: number
}

const CATEGORY_COLORS = {
  similar: { bg: 'bg-green-100', border: 'border-green-400', text: 'text-green-800' },
  different: { bg: 'bg-red-100', border: 'border-red-400', text: 'text-red-800' },
  unique_a: { bg: 'bg-blue-100', border: 'border-blue-400', text: 'text-blue-800' },
  unique_b: { bg: 'bg-purple-100', border: 'border-purple-400', text: 'text-purple-800' },
}

const CATEGORY_LABELS = {
  similar: 'Similar in Both',
  different: 'Different',
  unique_a: 'Unique to A',
  unique_b: 'Unique to B',
}

export function CompareContrast({
  diagramA,
  diagramB,
  expectedCategories,
  highlightMatching = true,
  instructions = 'Compare the two diagrams and categorize each structure.',
  storeProgress,
  onAction,
}: CompareContrastProps) {
  // Layer 3: Initialize from storeProgress for restoration
  const [categorizations, setCategorizations] = useState<Record<string, string>>(
    storeProgress?.categorizations ?? {}
  )
  const [selectedZone, setSelectedZone] = useState<string | null>(null)
  const [isSubmitted, setIsSubmitted] = useState(storeProgress?.isSubmitted ?? false)
  const [result, setResult] = useState<CompareResult | null>(null)

  // Combine all zones from both diagrams
  const allZones = [
    ...(diagramA?.zones || []).map((z) => ({ ...z, diagram: 'A' })),
    ...(diagramB?.zones || []).map((z) => ({ ...z, diagram: 'B' })),
  ]

  const handleZoneClick = useCallback((zoneId: string) => {
    if (isSubmitted) return
    setSelectedZone(zoneId)
  }, [isSubmitted])

  const handleCategorySelect = useCallback(
    (category: 'similar' | 'different' | 'unique_a' | 'unique_b') => {
      if (!selectedZone || isSubmitted) return

      setCategorizations((prev) => ({
        ...prev,
        [selectedZone]: category,
      }))
      onAction?.({ type: 'categorize', mechanic: 'compare_contrast', zoneId: selectedZone, category })
      setSelectedZone(null)
    },
    [selectedZone, isSubmitted, onAction]
  )

  const handleSubmit = useCallback(() => {
    // Dispatch to store — store handles scoring and completion
    const actionResult = onAction?.({ type: 'submit_compare', mechanic: 'compare_contrast' })

    // Use ActionResult for visual feedback
    const correctCount = actionResult?.data?.correctCount as number ?? 0
    const totalCount = actionResult?.data?.totalCount as number ?? Object.keys(expectedCategories).length

    const compareResult: CompareResult = {
      isCorrect: actionResult?.isCorrect ?? false,
      score: totalCount > 0 ? Math.round((correctCount / totalCount) * 100) : 0,
      maxScore: 100,
      categorizations,
      correctCount,
      totalCount,
    }

    setResult(compareResult)
    setIsSubmitted(true)
  }, [categorizations, expectedCategories, onAction])

  const handleReset = useCallback(() => {
    setCategorizations({})
    setSelectedZone(null)
    setIsSubmitted(false)
    setResult(null)
  }, [])

  const renderDiagram = (diagram: ComparableDiagram, diagramKey: 'A' | 'B') => (
    <div className="relative">
      <h3 className="text-sm font-semibold text-gray-700 mb-2">{diagram.name}</h3>
      <div className="relative border-2 border-gray-200 rounded-lg overflow-hidden">
        <img
          src={diagram.imageUrl}
          alt={diagram.name}
          className="w-full h-auto"
        />
        {/* Overlay zones */}
        {(diagram.zones || []).map((zone) => {
          const category = categorizations[zone.id]
          const colors = category ? CATEGORY_COLORS[category as keyof typeof CATEGORY_COLORS] : null
          const isSelected = selectedZone === zone.id
          const isCorrect = isSubmitted && expectedCategories[zone.id] === category
          const isIncorrect = isSubmitted && category && expectedCategories[zone.id] !== category

          return (
            <div
              key={zone.id}
              onClick={() => handleZoneClick(zone.id)}
              className={`
                absolute cursor-pointer border-2 rounded
                transition-all duration-200
                ${isSelected ? 'ring-4 ring-blue-400 ring-opacity-50' : ''}
                ${colors ? `${colors.bg} ${colors.border}` : 'border-gray-400 bg-gray-100 bg-opacity-50'}
                ${isCorrect ? 'ring-4 ring-green-400' : ''}
                ${isIncorrect ? 'ring-4 ring-red-400' : ''}
                ${!isSubmitted ? 'hover:border-blue-400 hover:bg-blue-50' : ''}
              `}
              style={{
                left: `${zone.x}%`,
                top: `${zone.y}%`,
                width: `${zone.width}%`,
                height: `${zone.height}%`,
              }}
            >
              <span className="absolute top-0 left-0 text-xs bg-white px-1 rounded-br truncate max-w-full">
                {zone.label}
              </span>
            </div>
          )
        })}
      </div>
    </div>
  )

  // Count categorized items
  const categorizedCount = Object.keys(categorizations).length
  const totalRequired = Object.keys(expectedCategories).length

  return (
    <div className="w-full max-w-6xl mx-auto p-4">
      {/* Instructions */}
      <div className="mb-4 p-3 bg-blue-50 rounded-lg">
        <p className="text-sm text-blue-800">{instructions}</p>
      </div>

      {/* Progress */}
      <div className="mb-4 flex items-center justify-between text-sm text-gray-600">
        <span>Progress: {categorizedCount} / {totalRequired} categorized</span>
        {selectedZone && <span className="text-blue-600">Select a category below</span>}
      </div>

      {/* Side-by-side diagrams */}
      <div className="grid grid-cols-2 gap-6 mb-6">
        {renderDiagram(diagramA, 'A')}
        {renderDiagram(diagramB, 'B')}
      </div>

      {/* Category selection */}
      {selectedZone && !isSubmitted && (
        <div className="mb-4 p-4 bg-gray-50 rounded-lg">
          <p className="text-sm text-gray-700 mb-3">
            Categorize: <span className="font-semibold">{allZones.find(z => z.id === selectedZone)?.label}</span>
          </p>
          <div className="flex flex-wrap gap-2">
            {Object.entries(CATEGORY_LABELS).map(([key, label]) => {
              const colors = CATEGORY_COLORS[key as keyof typeof CATEGORY_COLORS]
              return (
                <button
                  key={key}
                  onClick={() => handleCategorySelect(key as 'similar' | 'different' | 'unique_a' | 'unique_b')}
                  className={`px-4 py-2 rounded-lg border-2 ${colors.bg} ${colors.border} ${colors.text} hover:opacity-80 transition-opacity`}
                >
                  {label}
                </button>
              )
            })}
          </div>
        </div>
      )}

      {/* Legend */}
      <div className="mb-4 p-3 bg-gray-50 rounded-lg">
        <p className="text-xs text-gray-600 mb-2 font-medium">Category Legend:</p>
        <div className="flex flex-wrap gap-3">
          {Object.entries(CATEGORY_LABELS).map(([key, label]) => {
            const colors = CATEGORY_COLORS[key as keyof typeof CATEGORY_COLORS]
            return (
              <span key={key} className={`px-2 py-1 rounded text-xs ${colors.bg} ${colors.text}`}>
                {label}
              </span>
            )
          })}
        </div>
      </div>

      {/* Results */}
      {isSubmitted && result && (
        <div
          className={`mb-4 p-4 rounded-lg ${
            result.isCorrect
              ? 'bg-green-100 border border-green-300'
              : 'bg-amber-100 border border-amber-300'
          }`}
        >
          <div className="flex items-center justify-between">
            <div>
              <p className="font-semibold text-gray-800">
                {result.isCorrect
                  ? 'Perfect! All structures categorized correctly.'
                  : `${result.correctCount} of ${result.totalCount} structures categorized correctly.`}
              </p>
            </div>
            <div className="text-2xl font-bold">
              {result.score}%
            </div>
          </div>
        </div>
      )}

      {/* Action buttons */}
      <div className="flex gap-3">
        {!isSubmitted ? (
          <button
            onClick={handleSubmit}
            disabled={categorizedCount < totalRequired}
            className={`flex-1 py-2 px-4 rounded-lg font-medium transition-colors
              ${categorizedCount >= totalRequired
                ? 'bg-blue-600 text-white hover:bg-blue-700'
                : 'bg-gray-300 text-gray-500 cursor-not-allowed'
              }`}
          >
            Check Answers ({categorizedCount}/{totalRequired})
          </button>
        ) : (
          <button
            onClick={handleReset}
            className="flex-1 py-2 px-4 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition-colors font-medium"
          >
            Try Again
          </button>
        )}
      </div>
    </div>
  )
}

export default CompareContrast
