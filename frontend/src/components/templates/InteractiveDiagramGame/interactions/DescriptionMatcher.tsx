'use client'

import React, { useState, useCallback, useMemo, useRef } from 'react'
import { Zone, Label, MechanicAction, ActionResult } from '../types'
import {
  DndContext,
  DragEndEvent,
  useDraggable,
  useDroppable,
  DragOverlay,
} from '@dnd-kit/core'

interface DescriptionMatcherProps {
  zones: Zone[]
  labels: Label[]
  descriptions?: Record<string, string>  // QW-2: pedagogical descriptions from descriptionMatchingConfig
  assetUrl?: string  // Diagram image URL
  mode?: 'click_zone' | 'drag_description' | 'multiple_choice'
  showHints?: boolean
  storeProgress?: { currentIndex: number; matches: MatchResult[]; mode: string } | null  // MF-1: store integration
  /** V4 unified action dispatch */
  onAction?: (action: MechanicAction) => ActionResult | null
}

interface MatchResult {
  labelId: string
  zoneId: string
  isCorrect: boolean
}

interface ActiveDescription {
  text: string
  correctZoneId: string
}

/**
 * DescriptionMatcher Component (Preset 2)
 *
 * Provides description-based matching interaction modes:
 * - click_zone: Show description, user clicks the correct zone
 * - drag_description: Drag descriptions to zones (reverse drag-drop)
 * - multiple_choice: Select correct description for highlighted zone
 */
// CB-FIX-2: Normalize mode strings to canonical values
const VALID_MODES = new Set(['click_zone', 'drag_description', 'multiple_choice']);
function normalizeMode(mode: string | undefined): 'click_zone' | 'drag_description' | 'multiple_choice' {
  if (mode && VALID_MODES.has(mode)) return mode as 'click_zone' | 'drag_description' | 'multiple_choice';
  // Handle common aliases
  if (mode === 'drag') return 'drag_description';
  if (mode === 'click' || mode === 'click_to_identify') return 'click_zone';
  if (mode === 'multiple' || mode === 'mc') return 'multiple_choice';
  return 'click_zone'; // safe default
}

export const DescriptionMatcher: React.FC<DescriptionMatcherProps> = ({
  zones,
  labels,
  descriptions,
  assetUrl,
  mode: rawMode = 'click_zone',
  showHints = false,
  storeProgress,
  onAction,
}) => {
  // CB-FIX-2: Validate and normalize mode
  const mode = normalizeMode(rawMode);

  // MF-1: Initialize from storeProgress if resuming
  const [currentIndex, setCurrentIndex] = useState(storeProgress?.currentIndex ?? 0)
  const [matches, setMatches] = useState<MatchResult[]>(storeProgress?.matches ?? [])
  const [feedback, setFeedback] = useState<string | null>(null)
  const [selectedZone, setSelectedZone] = useState<string | null>(null)

  // Get zones that have descriptions (QW-2: use pedagogical descriptions if provided)
  const zonesWithDescriptions = useMemo(() => {
    if (descriptions) {
      return zones
        .filter(z => descriptions[z.id] || (z.description && z.description.trim().length > 0))
        .map(z => ({
          ...z,
          description: descriptions[z.id] || z.description,
        }));
    }
    return zones.filter(z => z.description && z.description.trim().length > 0)
  }, [zones, descriptions])

  // QW-6: Stable shuffle — only shuffle once per zone set, not on every render
  const zoneIdsKey = useMemo(() => zonesWithDescriptions.map(z => z.id).sort().join(','), [zonesWithDescriptions]);
  const shuffleOrderRef = useRef<string[]>([]);
  const shuffledZones = useMemo(() => {
    // Only reshuffle when the zone set actually changes
    const ids = zonesWithDescriptions.map(z => z.id);
    const currentKey = ids.sort().join(',');
    if (shuffleOrderRef.current.length === 0 || shuffleOrderRef.current.join(',') !== ids.join(',')) {
      shuffleOrderRef.current = [...zonesWithDescriptions.map(z => z.id)].sort(() => Math.random() - 0.5);
    }
    return shuffleOrderRef.current.map(id => zonesWithDescriptions.find(z => z.id === id)!).filter(Boolean);
  }, [zoneIdsKey, zonesWithDescriptions])

  const currentZone = shuffledZones[currentIndex]

  const handleZoneClick = useCallback((zoneId: string) => {
    if (!currentZone) return

    // Dispatch to store — store handles scoring and completion
    const actionResult = onAction?.({ type: 'description_match', mechanic: 'description_matching', labelId: currentZone.id, zoneId })
    const isCorrect = actionResult?.isCorrect ?? (zoneId === currentZone.id)

    const result: MatchResult = {
      labelId: currentZone.id,
      zoneId,
      isCorrect,
    }

    setMatches(prev => [...prev, result])

    if (isCorrect) {
      setFeedback('Correct!')
      setSelectedZone(zoneId)
    } else {
      setFeedback(`Incorrect. The description refers to ${currentZone.label}.`)
    }

    // Move to next after delay
    setTimeout(() => {
      setFeedback(null)
      setSelectedZone(null)
      if (currentIndex + 1 < shuffledZones.length) {
        setCurrentIndex(prev => prev + 1)
      }
      // Store detects completion via recordDescriptionMatch
    }, 1500)
  }, [currentZone, currentIndex, shuffledZones.length, onAction])

  if (mode === 'click_zone') {
    return (
      <div className="description-matcher">
        {/* Progress indicator */}
        <div className="mb-4 flex items-center justify-between">
          <span className="text-sm text-gray-600">
            Question {currentIndex + 1} of {shuffledZones.length}
          </span>
          <div className="w-48 h-2 bg-gray-200 rounded-full overflow-hidden">
            <div
              className="h-full bg-blue-500 transition-all duration-300"
              style={{ width: `${((currentIndex) / shuffledZones.length) * 100}%` }}
            />
          </div>
        </div>

        {/* Description prompt */}
        {currentZone && (
          <div className="mb-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
            <p className="text-sm text-blue-600 font-medium mb-1">
              Click the structure that matches this description:
            </p>
            <p className="text-lg text-gray-800">
              "{currentZone.description}"
            </p>
            {showHints && currentZone.hint && (
              <p className="mt-2 text-sm text-gray-500 italic">
                Hint: {currentZone.hint}
              </p>
            )}
          </div>
        )}

        {/* Feedback */}
        {feedback && (
          <div
            className={`mb-4 p-3 rounded-lg text-center font-medium ${
              feedback.startsWith('Correct')
                ? 'bg-green-100 text-green-800'
                : 'bg-red-100 text-red-800'
            }`}
          >
            {feedback}
          </div>
        )}

        {/* Diagram image */}
        {assetUrl && (
          <div className="mb-4 flex justify-center">
            <img
              src={assetUrl}
              alt="Diagram"
              className="max-w-full max-h-[400px] rounded-lg border border-gray-200 object-contain"
            />
          </div>
        )}

        {/* Zone buttons for click selection */}
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
          {zones.map(zone => (
            <button
              key={zone.id}
              onClick={() => handleZoneClick(zone.id)}
              disabled={!!feedback}
              className={`
                p-3 rounded-lg border-2 text-left transition-all
                ${selectedZone === zone.id
                  ? 'border-green-500 bg-green-50'
                  : 'border-gray-200 hover:border-blue-300 hover:bg-blue-50'
                }
                ${feedback ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
              `}
            >
              <span className="font-medium text-gray-800">{zone.label}</span>
            </button>
          ))}
        </div>

        {/* Results summary */}
        {matches.length > 0 && (
          <div className="mt-6 p-4 bg-gray-50 rounded-lg">
            <h4 className="text-sm font-medium text-gray-700 mb-2">Progress:</h4>
            <div className="flex flex-wrap gap-2">
              {matches.map((match, idx) => (
                <span
                  key={idx}
                  className={`px-2 py-1 rounded text-xs font-medium ${
                    match.isCorrect
                      ? 'bg-green-100 text-green-800'
                      : 'bg-red-100 text-red-800'
                  }`}
                >
                  {idx + 1}. {match.isCorrect ? 'Correct' : 'Incorrect'}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>
    )
  }

  // Multiple choice mode
  if (mode === 'multiple_choice') {
    // Fix 6.6: Memoize MC options by zone ID to prevent reshuffle on re-render
    // eslint-disable-next-line react-hooks/exhaustive-deps
    const options = useMemo(() => {
      if (!currentZone) return []

      const correct = currentZone
      const distractors = zones
        .filter(z => z.id !== correct.id && z.description)
        .sort(() => Math.random() - 0.5)
        .slice(0, 3)

      return [correct, ...distractors].sort(() => Math.random() - 0.5)
    }, [currentZone?.id]) // Only re-shuffle when zone changes, not on every render

    return (
      <div className="description-matcher multiple-choice">
        {/* Progress */}
        <div className="mb-4 flex items-center justify-between">
          <span className="text-sm text-gray-600">
            Question {currentIndex + 1} of {shuffledZones.length}
          </span>
        </div>

        {/* Highlighted zone name */}
        {currentZone && (
          <div className="mb-4 p-4 bg-amber-50 border border-amber-200 rounded-lg text-center">
            <p className="text-sm text-amber-600 font-medium mb-1">
              Which description matches this structure?
            </p>
            <p className="text-2xl font-bold text-gray-800">{currentZone.label}</p>
          </div>
        )}

        {/* Description options */}
        <div className="space-y-3">
          {options.map((option, idx) => (
            <button
              key={option.id}
              onClick={() => handleZoneClick(option.id)}
              disabled={!!feedback}
              className={`
                w-full p-4 rounded-lg border-2 text-left transition-all
                ${selectedZone === option.id
                  ? 'border-green-500 bg-green-50'
                  : 'border-gray-200 hover:border-blue-300 hover:bg-blue-50'
                }
                ${feedback ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
              `}
            >
              <span className="inline-block w-6 h-6 rounded-full bg-gray-200 text-center mr-3">
                {String.fromCharCode(65 + idx)}
              </span>
              <span className="text-gray-800">{option.description}</span>
            </button>
          ))}
        </div>

        {/* Feedback */}
        {feedback && (
          <div
            className={`mt-4 p-3 rounded-lg text-center font-medium ${
              feedback.startsWith('Correct')
                ? 'bg-green-100 text-green-800'
                : 'bg-red-100 text-red-800'
            }`}
          >
            {feedback}
          </div>
        )}
      </div>
    )
  }

  // ============================================================
  // DRAG_DESCRIPTION MODE: Drag descriptions to matching zones
  // ============================================================

  // State for drag mode
  const [matchedPairs, setMatchedPairs] = useState<Map<string, string>>(new Map())
  const [dragFeedback, setDragFeedback] = useState<{ zoneId: string; correct: boolean } | null>(null)
  const [activeDragId, setActiveDragId] = useState<string | null>(null)

  // Get descriptions from zones for dragging
  const dragDescriptions = useMemo(() => {
    return zonesWithDescriptions
      .map(z => ({ id: z.id, text: z.description || '', label: z.label }))
      .sort(() => Math.random() - 0.5) // Shuffle
  }, [zonesWithDescriptions])

  // Handle drag end
  const handleDragEnd = useCallback((event: DragEndEvent) => {
    const { active, over } = event
    setActiveDragId(null)

    if (!over) return

    const descriptionId = active.id as string
    const zoneId = over.id as string

    // Find the zone and check if match is correct
    const zone = zones.find(z => z.id === zoneId)
    const description = dragDescriptions.find(d => d.id === descriptionId)

    if (!zone || !description) return

    // Check if this description belongs to this zone
    const isCorrect = descriptionId === zoneId

    // Show feedback
    setDragFeedback({ zoneId, correct: isCorrect })

    // Dispatch to store — store handles scoring and completion
    const actionResult = onAction?.({ type: 'description_match', mechanic: 'description_matching', labelId: descriptionId, zoneId })
    const wasCorrect = actionResult?.isCorrect ?? isCorrect

    if (wasCorrect) {
      setMatchedPairs(prev => {
        const newMap = new Map(prev)
        newMap.set(zoneId, description.text)
        return newMap
      })
    }

    const result: MatchResult = {
      labelId: descriptionId,
      zoneId,
      isCorrect: wasCorrect,
    }
    setMatches(prev => [...prev, result])

    // Clear feedback — store detects completion
    setTimeout(() => {
      setDragFeedback(null)
    }, 1000)
  }, [zones, dragDescriptions, matchedPairs, onAction])

  // Draggable Description Component
  const DraggableDescription = ({ id, text, isUsed }: { id: string; text: string; isUsed: boolean }) => {
    const { attributes, listeners, setNodeRef, transform, isDragging } = useDraggable({
      id,
      disabled: isUsed,
    })

    const style = transform ? {
      transform: `translate(${transform.x}px, ${transform.y}px)`,
    } : undefined

    return (
      <div
        ref={setNodeRef}
        style={style}
        {...listeners}
        {...attributes}
        className={`
          p-3 rounded-lg border-2 transition-all text-sm
          ${isUsed
            ? 'bg-gray-100 border-gray-300 text-gray-400 cursor-not-allowed'
            : 'bg-white border-blue-400 hover:border-blue-600 hover:shadow-md cursor-grab'
          }
          ${isDragging ? 'shadow-xl scale-105 z-50 opacity-80' : ''}
        `}
      >
        {text}
      </div>
    )
  }

  // Droppable Zone Component
  const DroppableZone = ({ zone, matched, feedbackState }: {
    zone: Zone;
    matched?: string;
    feedbackState?: { correct: boolean } | null
  }) => {
    const { isOver, setNodeRef } = useDroppable({ id: zone.id })

    const isFeedback = feedbackState !== undefined && feedbackState !== null

    return (
      <div
        ref={setNodeRef}
        className={`
          absolute flex items-center justify-center rounded-full
          border-2 transition-all duration-200 text-center
          ${isOver && !matched ? 'border-blue-500 bg-blue-100/70 scale-110 shadow-lg' : ''}
          ${matched ? 'border-green-500 bg-green-100/70' : 'border-gray-400 bg-white/50 hover:bg-gray-100/50'}
          ${isFeedback && feedbackState.correct ? 'border-green-500 bg-green-200/80 animate-pulse' : ''}
          ${isFeedback && !feedbackState.correct ? 'border-red-500 bg-red-200/80 animate-shake' : ''}
        `}
        style={{
          left: `${(zone.x ?? 50) - ((zone.radius || 5))}%`,
          top: `${(zone.y ?? 50) - ((zone.radius || 5))}%`,
          width: `${(zone.radius || 5) * 2}%`,
          height: `${(zone.radius || 5) * 2}%`,
        }}
      >
        <span className="text-xs font-medium text-gray-700 px-1 truncate max-w-full">
          {zone.label}
        </span>
        {matched && (
          <div className="absolute -bottom-1 left-1/2 -translate-x-1/2 translate-y-full
                          bg-green-100 text-green-800 text-xs px-2 py-1 rounded shadow
                          whitespace-nowrap max-w-[200px] truncate z-10">
            ✓ Matched
          </div>
        )}
      </div>
    )
  }

  return (
    <DndContext
      onDragStart={e => setActiveDragId(e.active.id as string)}
      onDragEnd={handleDragEnd}
    >
      <div className="description-matcher drag-mode">
        {/* Header */}
        <div className="mb-4 p-3 bg-blue-50 border border-blue-200 rounded-lg">
          <h3 className="font-semibold text-blue-800 flex items-center gap-2">
            <span className="text-lg">📝</span>
            Drag each description to its matching zone
          </h3>
          <p className="text-sm text-blue-600 mt-1">
            {matchedPairs.size} of {zonesWithDescriptions.length} matched
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Description Pool */}
          <div className="space-y-3 p-4 bg-gray-50 rounded-xl max-h-[500px] overflow-y-auto">
            <h4 className="font-medium text-gray-700 mb-2">Descriptions</h4>
            <div className="space-y-2">
              {dragDescriptions.map(desc => (
                <DraggableDescription
                  key={desc.id}
                  id={desc.id}
                  text={desc.text}
                  isUsed={matchedPairs.has(desc.id)}
                />
              ))}
            </div>
          </div>

          {/* Diagram with Droppable Zones */}
          <div className="relative bg-gray-100 rounded-xl overflow-hidden min-h-[400px]">
            {/* Diagram background */}
            {assetUrl && (
              <img
                src={assetUrl}
                alt="Diagram"
                className="w-full h-auto block"
              />
            )}
            {/* Zone indicators */}
            {zones.map(zone => (
              <DroppableZone
                key={zone.id}
                zone={zone}
                matched={matchedPairs.get(zone.id)}
                feedbackState={dragFeedback?.zoneId === zone.id ? dragFeedback : null}
              />
            ))}

            {/* Empty state if no zones */}
            {zones.length === 0 && (
              <div className="absolute inset-0 flex items-center justify-center text-gray-500">
                No zones available
              </div>
            )}
          </div>
        </div>

        {/* Drag Overlay */}
        <DragOverlay>
          {activeDragId && (
            <div className="p-3 rounded-lg border-2 border-blue-500 bg-blue-50 shadow-xl text-sm">
              {dragDescriptions.find(d => d.id === activeDragId)?.text}
            </div>
          )}
        </DragOverlay>
      </div>
    </DndContext>
  )
}

export default DescriptionMatcher
