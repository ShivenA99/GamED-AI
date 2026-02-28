'use client'

import React, { useState, useCallback } from 'react'
import {
  DndContext,
  DragOverlay,
  closestCorners,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  DragEndEvent,
  DragStartEvent,
  useDroppable,
  useDraggable,
} from '@dnd-kit/core'
import { sortableKeyboardCoordinates } from '@dnd-kit/sortable'

/**
 * SortingCategories - Sort items into categories interaction component
 *
 * Users drag items from a pool into predefined categories.
 * Supports multiple categories and validation.
 */

export interface SortableItem {
  id: string
  text: string
  correctCategoryId: string
  correctCategoryIds?: string[]  // Fix 5.2: multi-category support
  description?: string
  difficulty?: string
}

export interface Category {
  id: string
  label: string
  description?: string
  color?: string
}

export interface SortingCategoriesProps {
  items: SortableItem[]
  categories: Category[]
  onComplete: (result: SortingResult) => void
  allowPartialCredit?: boolean
  showCategoryHints?: boolean
  instructions?: string
  // Store integration props (Fix 1.7h) — optional for standalone use
  storeProgress?: { itemCategories: Record<string, string | null>; isSubmitted: boolean; correctCount: number; totalCount: number } | null
  onPlacementChange?: (itemId: string, categoryId: string | null) => void
  onStoreSubmit?: () => void
}

export interface SortingResult {
  isCorrect: boolean
  score: number
  maxScore: number
  categorizations: Record<string, string>
  correctCount: number
  totalCount: number
}

// Draggable item component
function DraggableItem({
  item,
  isInCategory,
}: {
  item: SortableItem
  isInCategory: boolean
}) {
  const { attributes, listeners, setNodeRef, isDragging } = useDraggable({
    id: item.id,
  })

  return (
    <div
      ref={setNodeRef}
      {...listeners}
      {...attributes}
      className={`
        p-3 rounded-lg border-2 cursor-grab active:cursor-grabbing
        transition-all duration-200 select-none
        ${isDragging ? 'opacity-50 scale-95' : ''}
        ${isInCategory
          ? 'bg-gray-50 border-gray-200'
          : 'bg-white border-gray-300 shadow-sm hover:shadow-md hover:border-blue-300'
        }
      `}
    >
      <p className="text-sm font-medium text-gray-800">{item.text}</p>
      {item.description && (
        <p className="text-xs text-gray-500 mt-1">{item.description}</p>
      )}
    </div>
  )
}

// Droppable category component
function DroppableCategory({
  category,
  items,
  isCorrect,
  showFeedback,
}: {
  category: Category
  items: SortableItem[]
  isCorrect?: boolean
  showFeedback: boolean
}) {
  const { setNodeRef, isOver } = useDroppable({
    id: category.id,
  })

  // Static Tailwind class map to avoid dynamic class generation (Tailwind purge-safe)
  const categoryTextColorMap: Record<string, string> = {
    blue: 'text-blue-700',
    green: 'text-green-700',
    purple: 'text-purple-700',
    orange: 'text-orange-700',
    red: 'text-red-700',
    teal: 'text-teal-700',
    yellow: 'text-yellow-700',
    pink: 'text-pink-700',
  }
  const textColorClass = categoryTextColorMap[category.color || 'blue'] || 'text-blue-700'

  return (
    <div
      ref={setNodeRef}
      className={`
        min-h-[150px] p-3 rounded-lg border-2 transition-all duration-200
        ${isOver ? 'bg-blue-50 border-blue-400 scale-[1.02]' : 'bg-gray-50 border-gray-200'}
        ${showFeedback && isCorrect === true ? 'ring-2 ring-green-400' : ''}
        ${showFeedback && isCorrect === false ? 'ring-2 ring-red-400' : ''}
      `}
    >
      <div className="flex items-center justify-between mb-2">
        <h3 className={`text-sm font-semibold ${textColorClass}`}>
          {category.label}
        </h3>
        <span className="text-xs text-gray-500 bg-white px-2 py-0.5 rounded-full">
          {items.length} item{items.length !== 1 ? 's' : ''}
        </span>
      </div>
      {category.description && (
        <p className="text-xs text-gray-500 mb-2">{category.description}</p>
      )}
      <div className="space-y-2">
        {items.map((item) => (
          <DraggableItem key={item.id} item={item} isInCategory={true} />
        ))}
        {items.length === 0 && (
          <p className="text-xs text-gray-400 text-center py-4">
            Drop items here
          </p>
        )}
      </div>
    </div>
  )
}

export function SortingCategories({
  items: initialItems,
  categories,
  onComplete,
  allowPartialCredit = true,
  showCategoryHints = true,
  instructions = 'Drag each item to the correct category.',
  storeProgress,
  onPlacementChange,
  onStoreSubmit,
}: SortingCategoriesProps) {
  // Track which category each item is in (null = unsorted pool)
  const [itemCategories, setItemCategories] = useState<Record<string, string | null>>(() => {
    const initial: Record<string, string | null> = {}
    initialItems.forEach((item) => {
      initial[item.id] = null
    })
    return initial
  })

  const [activeId, setActiveId] = useState<string | null>(null)
  const [isSubmitted, setIsSubmitted] = useState(false)
  const [result, setResult] = useState<SortingResult | null>(null)

  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  )

  // Get unsorted items (in pool)
  const unsortedItems = initialItems.filter((item) => itemCategories[item.id] === null)

  // Get items for each category
  const getCategoryItems = (categoryId: string) => {
    return initialItems.filter((item) => itemCategories[item.id] === categoryId)
  }

  const handleDragStart = useCallback((event: DragStartEvent) => {
    setActiveId(event.active.id as string)
  }, [])

  const handleDragEnd = useCallback(
    (event: DragEndEvent) => {
      const { active, over } = event
      setActiveId(null)

      if (!over) {
        // Dropped outside - return to pool
        setItemCategories((prev) => ({
          ...prev,
          [active.id]: null,
        }))
        return
      }

      // Check if dropped on a category
      const categoryId = categories.find((c) => c.id === over.id)?.id
      if (categoryId) {
        setItemCategories((prev) => ({
          ...prev,
          [active.id]: categoryId,
        }))
        onPlacementChange?.(active.id as string, categoryId)
      } else if (over.id === 'pool') {
        // Return to pool
        setItemCategories((prev) => ({
          ...prev,
          [active.id]: null,
        }))
        onPlacementChange?.(active.id as string, null)
      }
    },
    [categories]
  )

  const handleSubmit = useCallback(() => {
    // Calculate score
    let correctCount = 0
    const totalCount = initialItems.length

    const categorizations: Record<string, string> = {}
    for (const item of initialItems) {
      const assignedCategory = itemCategories[item.id]
      if (assignedCategory) {
        categorizations[item.id] = assignedCategory
        const isItemCorrect = item.correctCategoryIds?.length
          ? item.correctCategoryIds.includes(assignedCategory)
          : assignedCategory === item.correctCategoryId;
        if (isItemCorrect) {
          correctCount++
        }
      }
    }

    const isCorrect = correctCount === totalCount
    const score = allowPartialCredit
      ? Math.round((correctCount / totalCount) * 100)
      : isCorrect
      ? 100
      : 0

    const sortingResult: SortingResult = {
      isCorrect,
      score,
      maxScore: 100,
      categorizations,
      correctCount,
      totalCount,
    }

    setResult(sortingResult)
    setIsSubmitted(true)
    onStoreSubmit?.()
    onComplete(sortingResult)
  }, [initialItems, itemCategories, allowPartialCredit, onComplete, onStoreSubmit])

  const handleReset = useCallback(() => {
    const initial: Record<string, string | null> = {}
    initialItems.forEach((item) => {
      initial[item.id] = null
    })
    setItemCategories(initial)
    setIsSubmitted(false)
    setResult(null)
  }, [initialItems])

  // Check if all items are sorted
  const allSorted = unsortedItems.length === 0

  // Check correctness for feedback
  const getCategoryCorrectness = (categoryId: string) => {
    if (!isSubmitted) return undefined
    const categoryItems = getCategoryItems(categoryId)
    return categoryItems.every((item) =>
      item.correctCategoryIds?.length
        ? item.correctCategoryIds.includes(categoryId)
        : item.correctCategoryId === categoryId
    )
  }

  return (
    <div className="w-full max-w-4xl mx-auto p-4">
      {/* Instructions */}
      <div className="mb-4 p-3 bg-blue-50 rounded-lg">
        <p className="text-sm text-blue-800">{instructions}</p>
      </div>

      <DndContext
        sensors={sensors}
        collisionDetection={closestCorners}
        onDragStart={handleDragStart}
        onDragEnd={handleDragEnd}
      >
        {/* Unsorted items pool */}
        {unsortedItems.length > 0 && (
          <div className="mb-6">
            <h3 className="text-sm font-semibold text-gray-700 mb-2">
              Items to Sort ({unsortedItems.length})
            </h3>
            <div
              className="flex flex-wrap gap-2 p-4 bg-white border-2 border-dashed border-gray-300 rounded-lg min-h-[100px]"
            >
              {unsortedItems.map((item) => (
                <DraggableItem key={item.id} item={item} isInCategory={false} />
              ))}
            </div>
          </div>
        )}

        {/* Categories */}
        <div className="mb-4">
          <h3 className="text-sm font-semibold text-gray-700 mb-2">Categories</h3>
          <div className="grid gap-4" style={{ gridTemplateColumns: `repeat(${Math.min(categories.length, 4)}, minmax(0, 1fr))` }}>
            {categories.map((category) => (
              <DroppableCategory
                key={category.id}
                category={category}
                items={getCategoryItems(category.id)}
                isCorrect={getCategoryCorrectness(category.id)}
                showFeedback={isSubmitted}
              />
            ))}
          </div>
        </div>

        {/* Drag overlay */}
        <DragOverlay>
          {activeId ? (
            <div className="p-3 bg-white border-2 border-blue-400 rounded-lg shadow-lg">
              <p className="text-sm font-medium text-gray-800">
                {initialItems.find((i) => i.id === activeId)?.text}
              </p>
            </div>
          ) : null}
        </DragOverlay>
      </DndContext>

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
                  ? 'Perfect! All items sorted correctly.'
                  : `${result.correctCount} of ${result.totalCount} items sorted correctly.`}
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
            disabled={!allSorted}
            className={`flex-1 py-2 px-4 rounded-lg font-medium transition-colors
              ${allSorted
                ? 'bg-blue-600 text-white hover:bg-blue-700'
                : 'bg-gray-300 text-gray-500 cursor-not-allowed'
              }`}
          >
            {allSorted ? 'Check Answers' : `Sort all items first (${unsortedItems.length} remaining)`}
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

export default SortingCategories
