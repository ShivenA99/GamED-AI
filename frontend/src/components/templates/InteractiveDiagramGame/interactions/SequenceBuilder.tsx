'use client'

import React, { useState, useCallback } from 'react'
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  DragEndEvent,
} from '@dnd-kit/core'
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  useSortable,
  verticalListSortingStrategy,
} from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'

/**
 * SequenceBuilder - Drag-to-reorder sequence interaction component
 *
 * Users arrange elements in correct chronological or logical order.
 * Supports linear sequences with partial credit scoring.
 */

export interface SequenceItem {
  id: string
  text: string
  orderIndex: number
  description?: string
}

export interface SequenceBuilderProps {
  items: SequenceItem[]
  correctOrder: string[] // Array of item IDs in correct order
  allowPartialCredit: boolean
  onComplete: (result: SequenceResult) => void
  showPositionHints?: boolean
  animateOnComplete?: boolean
  instructions?: string
  // Store integration props (Fix 1.7h) — optional for standalone use
  storeProgress?: { currentOrder: string[]; isSubmitted: boolean; correctPositions: number; totalPositions: number } | null
  onOrderChange?: (newOrder: string[]) => void
  onStoreSubmit?: () => void
}

export interface SequenceResult {
  isCorrect: boolean
  score: number
  maxScore: number
  userOrder: string[]
  correctOrder: string[]
  correctPositions: number
  totalPositions: number
}

// Sortable item component
function SortableItem({
  item,
  isCorrect,
  showFeedback,
}: {
  item: SequenceItem
  isCorrect?: boolean
  showFeedback: boolean
}) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: item.id })

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  }

  return (
    <div
      ref={setNodeRef}
      style={style}
      {...attributes}
      {...listeners}
      className={`
        p-4 mb-2 rounded-lg border-2 cursor-grab active:cursor-grabbing
        transition-all duration-200
        ${isDragging ? 'shadow-lg scale-105 bg-blue-50 border-blue-400' : ''}
        ${showFeedback && isCorrect === true ? 'bg-green-50 border-green-400' : ''}
        ${showFeedback && isCorrect === false ? 'bg-red-50 border-red-400' : ''}
        ${!showFeedback && !isDragging ? 'bg-white border-gray-200 hover:border-blue-300' : ''}
      `}
    >
      <div className="flex items-center gap-3">
        <div className="text-gray-400">
          <svg
            className="w-5 h-5"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M4 8h16M4 16h16"
            />
          </svg>
        </div>
        <div className="flex-1">
          <p className="text-sm font-medium text-gray-800">{item.text}</p>
          {item.description && (
            <p className="text-xs text-gray-500 mt-1">{item.description}</p>
          )}
        </div>
        {showFeedback && (
          <div className="text-lg">
            {isCorrect ? (
              <span className="text-green-500">✓</span>
            ) : (
              <span className="text-red-500">✗</span>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

export function SequenceBuilder({
  items: initialItems,
  correctOrder,
  allowPartialCredit,
  onComplete,
  showPositionHints = false,
  animateOnComplete = true,
  instructions = 'Drag the items to arrange them in the correct order.',
  storeProgress,
  onOrderChange,
  onStoreSubmit,
}: SequenceBuilderProps) {
  const [items, setItems] = useState<SequenceItem[]>(() => {
    // Shuffle items initially
    return [...initialItems].sort(() => Math.random() - 0.5)
  })
  const [isSubmitted, setIsSubmitted] = useState(false)
  const [result, setResult] = useState<SequenceResult | null>(null)

  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  )

  const handleDragEnd = useCallback(
    (event: DragEndEvent) => {
      const { active, over } = event

      if (over && active.id !== over.id) {
        setItems((currentItems) => {
          const oldIndex = currentItems.findIndex((i) => i.id === active.id)
          const newIndex = currentItems.findIndex((i) => i.id === over.id)
          const newItems = arrayMove(currentItems, oldIndex, newIndex)
          // Notify store of order change (Fix 1.7h)
          onOrderChange?.(newItems.map((i) => i.id))
          return newItems
        })
      }
    },
    []
  )

  const handleSubmit = useCallback(() => {
    const userOrder = items.map((i) => i.id)

    // Calculate score
    let correctPositions = 0
    for (let i = 0; i < userOrder.length; i++) {
      if (userOrder[i] === correctOrder[i]) {
        correctPositions++
      }
    }

    const isCorrect = correctPositions === correctOrder.length
    const score = allowPartialCredit
      ? Math.round((correctPositions / correctOrder.length) * 100)
      : isCorrect
      ? 100
      : 0

    const sequenceResult: SequenceResult = {
      isCorrect,
      score,
      maxScore: 100,
      userOrder,
      correctOrder,
      correctPositions,
      totalPositions: correctOrder.length,
    }

    setResult(sequenceResult)
    setIsSubmitted(true)
    // Notify store of submission (Fix 1.7h)
    onStoreSubmit?.()
    onComplete(sequenceResult)
  }, [items, correctOrder, allowPartialCredit, onComplete, onStoreSubmit])

  const handleReset = useCallback(() => {
    setItems([...initialItems].sort(() => Math.random() - 0.5))
    setIsSubmitted(false)
    setResult(null)
  }, [initialItems])

  // Check if each item is in the correct position
  const getItemCorrectness = useCallback(
    (itemId: string, index: number) => {
      if (!isSubmitted) return undefined
      return correctOrder[index] === itemId
    },
    [isSubmitted, correctOrder]
  )

  return (
    <div className="w-full max-w-2xl mx-auto p-4">
      {/* Instructions */}
      <div className="mb-4 p-3 bg-blue-50 rounded-lg">
        <p className="text-sm text-blue-800">{instructions}</p>
      </div>

      {/* Position hints */}
      {showPositionHints && !isSubmitted && (
        <div className="mb-4 flex justify-between text-xs text-gray-500">
          <span>First</span>
          <span>Last</span>
        </div>
      )}

      {/* Sortable list */}
      <DndContext
        sensors={sensors}
        collisionDetection={closestCenter}
        onDragEnd={handleDragEnd}
      >
        <SortableContext
          items={items.map((i) => i.id)}
          strategy={verticalListSortingStrategy}
          disabled={isSubmitted}
        >
          <div className="min-h-[200px]">
            {items.map((item, index) => (
              <SortableItem
                key={item.id}
                item={item}
                isCorrect={getItemCorrectness(item.id, index)}
                showFeedback={isSubmitted}
              />
            ))}
          </div>
        </SortableContext>
      </DndContext>

      {/* Results */}
      {isSubmitted && result && (
        <div
          className={`mt-4 p-4 rounded-lg ${
            result.isCorrect
              ? 'bg-green-100 border border-green-300'
              : 'bg-amber-100 border border-amber-300'
          }`}
        >
          <div className="flex items-center justify-between">
            <div>
              <p className="font-semibold text-gray-800">
                {result.isCorrect
                  ? 'Perfect! All items are in the correct order.'
                  : `${result.correctPositions} of ${result.totalPositions} items in correct position.`}
              </p>
              {allowPartialCredit && !result.isCorrect && (
                <p className="text-sm text-gray-600 mt-1">
                  Partial credit: {result.score}%
                </p>
              )}
            </div>
            <div className="text-2xl font-bold">
              {result.score}%
            </div>
          </div>
        </div>
      )}

      {/* Action buttons */}
      <div className="mt-4 flex gap-3">
        {!isSubmitted ? (
          <button
            onClick={handleSubmit}
            className="flex-1 py-2 px-4 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium"
          >
            Check Order
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

export default SequenceBuilder
