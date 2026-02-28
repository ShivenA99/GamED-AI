'use client';

import React, { useState, useCallback, useMemo } from 'react';
import {
  DndContext, DragOverlay, DragStartEvent, DragEndEvent,
  useDroppable, useDraggable, closestCenter,
  PointerSensor, KeyboardSensor, useSensor, useSensors,
} from '@dnd-kit/core';
import { motion, AnimatePresence } from 'framer-motion';
import { SortingItem, SortingCategory, SortingConfig, MechanicAction, ActionResult } from '../types';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type SortMode = 'bucket' | 'venn_2' | 'venn_3' | 'matrix' | 'column';
type ItemCardType = 'text_only' | 'text_with_icon' | 'image_with_caption' | 'image_only' | 'rich_card';

interface EnhancedSortingProps {
  items: SortingItem[];
  categories: SortingCategory[];
  config?: SortingConfig;
  /** Source-of-truth progress from store. Used for restoring state on mount. */
  storeProgress?: { itemCategories: Record<string, string | null>; isSubmitted: boolean; correctCount: number; totalCount: number } | null;
  /** Unified action dispatch — the only output channel. */
  onAction: (action: MechanicAction) => ActionResult | null;
}

const DEFAULT_CATEGORY_COLORS = ['#6366f1', '#ec4899', '#f59e0b', '#10b981', '#8b5cf6', '#ef4444'];

function getCategoryColor(category: SortingCategory, index: number): string {
  return category.color || DEFAULT_CATEGORY_COLORS[index % DEFAULT_CATEGORY_COLORS.length];
}

// ---------------------------------------------------------------------------
// DraggableSortItem — Rich card for sorting
// ---------------------------------------------------------------------------

function DraggableSortItem({
  item,
  cardType = 'text_only',
  isDragging,
  isCorrect,
  isIncorrect,
  showFeedback,
  hideDifficulty = false,
}: {
  item: SortingItem;
  cardType?: ItemCardType;
  isDragging?: boolean;
  isCorrect?: boolean;
  isIncorrect?: boolean;
  showFeedback?: boolean;
  hideDifficulty?: boolean;
}) {
  const { attributes, listeners, setNodeRef, transform } = useDraggable({ id: item.id });

  const style: React.CSSProperties = {
    transform: transform ? `translate(${transform.x}px, ${transform.y}px)` : undefined,
    opacity: isDragging ? 0.4 : 1,
  };

  const borderColor = showFeedback
    ? isCorrect ? 'border-green-400' : isIncorrect ? 'border-red-400' : 'border-gray-200 dark:border-gray-600'
    : 'border-gray-200 dark:border-gray-600';

  const bgColor = showFeedback
    ? isCorrect ? 'bg-green-50 dark:bg-green-900/20' : isIncorrect ? 'bg-red-50 dark:bg-red-900/20' : 'bg-white dark:bg-gray-700'
    : 'bg-white dark:bg-gray-700';

  return (
    <div
      ref={setNodeRef}
      style={style}
      {...listeners}
      {...attributes}
      className={`rounded-lg border-2 ${borderColor} ${bgColor} shadow-sm cursor-grab active:cursor-grabbing transition-all duration-200 hover:shadow-md`}
    >
      {/* Image area */}
      {(cardType === 'image_with_caption' || cardType === 'image_only') && item.image && (
        <div className="rounded-t-md overflow-hidden bg-gray-100 dark:bg-gray-600">
          <img src={item.image} alt={item.content} className="w-full h-16 object-cover" />
        </div>
      )}

      <div className="px-3 py-2 flex items-center gap-2">
        {/* Difficulty indicator — hidden in unsorted pool to avoid leaking category info */}
        {!hideDifficulty && item.difficulty && (
          <span className={`w-2 h-2 rounded-full flex-shrink-0 ${
            item.difficulty === 'easy' ? 'bg-green-400' :
            item.difficulty === 'medium' ? 'bg-amber-400' : 'bg-red-400'
          }`} />
        )}

        <span className="text-sm font-medium text-gray-800 dark:text-gray-100 flex-1 min-w-0 truncate">
          {item.content}
        </span>

        {showFeedback && (
          <span className={`text-sm flex-shrink-0 ${isCorrect ? 'text-green-500' : 'text-red-500'}`}>
            {isCorrect ? '✓' : '✗'}
          </span>
        )}
      </div>

      {item.description && cardType !== 'image_only' && (
        <div className="px-3 pb-2">
          <p className="text-xs text-gray-500 dark:text-gray-400 line-clamp-2">{item.description}</p>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Bucket drop target
// ---------------------------------------------------------------------------

function BucketDropTarget({
  category,
  color,
  items,
  allItems,
  showFeedback,
  correctItemIds,
}: {
  category: SortingCategory;
  color: string;
  items: string[];
  allItems: SortingItem[];
  showFeedback: boolean;
  correctItemIds: Set<string>;
}) {
  const { isOver, setNodeRef } = useDroppable({ id: `cat-${category.id}` });

  const placedItems = items.map(id => allItems.find(i => i.id === id)).filter(Boolean) as SortingItem[];

  return (
    <div
      ref={setNodeRef}
      className={`
        rounded-xl border-2 transition-all duration-200 min-h-[140px] flex flex-col
        ${isOver ? 'scale-[1.02] shadow-lg' : 'shadow-sm'}
      `}
      style={{
        borderColor: isOver ? color : `${color}60`,
        backgroundColor: isOver ? `${color}10` : 'transparent',
      }}
    >
      {/* Category header */}
      <div
        className="px-4 py-2.5 rounded-t-lg flex items-center justify-between"
        style={{ backgroundColor: `${color}15` }}
      >
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full" style={{ backgroundColor: color }} />
          <span className="font-semibold text-sm text-gray-800 dark:text-gray-100">{category.label}</span>
        </div>
        <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-white/60 dark:bg-gray-800/60 text-gray-600 dark:text-gray-300">
          {placedItems.length}
        </span>
      </div>

      {/* Category description */}
      {category.description && (
        <p className="px-3 py-1 text-xs text-gray-500 dark:text-gray-400">{category.description}</p>
      )}

      {/* Dropped items */}
      <div className="flex-1 p-2 flex flex-col gap-1.5">
        {placedItems.length === 0 && (
          <div className="flex-1 flex items-center justify-center">
            <p className="text-xs text-gray-400 dark:text-gray-500 italic">Drop items here</p>
          </div>
        )}
        {placedItems.map(item => (
          <motion.div
            key={item.id}
            initial={{ scale: 0.8, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            className={`
              px-2.5 py-1.5 rounded-md text-xs font-medium border
              ${showFeedback && correctItemIds.has(item.id)
                ? 'bg-green-50 dark:bg-green-900/20 border-green-300 text-green-800 dark:text-green-200'
                : showFeedback
                ? 'bg-red-50 dark:bg-red-900/20 border-red-300 text-red-800 dark:text-red-200'
                : 'bg-gray-50 dark:bg-gray-600 border-gray-200 dark:border-gray-500 text-gray-700 dark:text-gray-200'}
            `}
          >
            {item.content}
            {showFeedback && (
              <span className="ml-1">{correctItemIds.has(item.id) ? '✓' : '✗'}</span>
            )}
          </motion.div>
        ))}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Venn Diagram (2 circles)
// ---------------------------------------------------------------------------

function VennDiagram2({
  categories,
  placements,
  allItems,
  showFeedback,
  correctItemIds,
}: {
  categories: SortingCategory[];
  placements: Record<string, string | null>;
  allItems: SortingItem[];
  showFeedback: boolean;
  correctItemIds: Set<string>;
}) {
  const [cat1, cat2] = categories;
  const color1 = getCategoryColor(cat1, 0);
  const color2 = getCategoryColor(cat2, 1);

  // Regions: A only, B only, A∩B, outside
  const regions = [
    { id: `cat-${cat1.id}`, label: `${cat1.label} only`, cx: 160, cy: 200 },
    { id: `cat-${cat2.id}`, label: `${cat2.label} only`, cx: 340, cy: 200 },
    { id: `cat-overlap-${cat1.id}-${cat2.id}`, label: 'Both', cx: 250, cy: 200 },
  ];

  return (
    <div className="relative w-full max-w-lg mx-auto">
      <svg viewBox="0 0 500 400" className="w-full">
        {/* Circle A */}
        <circle cx={200} cy={200} r={150} fill={`${color1}15`} stroke={color1} strokeWidth={2.5} />
        {/* Circle B */}
        <circle cx={300} cy={200} r={150} fill={`${color2}15`} stroke={color2} strokeWidth={2.5} />

        {/* Labels */}
        <text x={120} y={90} textAnchor="middle" className="text-sm font-semibold fill-gray-700 dark:fill-gray-200">{cat1.label}</text>
        <text x={380} y={90} textAnchor="middle" className="text-sm font-semibold fill-gray-700 dark:fill-gray-200">{cat2.label}</text>
        <text x={250} y={380} textAnchor="middle" className="text-xs fill-gray-500">Both</text>
      </svg>

      {/* Drop regions */}
      {regions.map(region => (
        <VennDropRegion
          key={region.id}
          id={region.id}
          cx={region.cx}
          cy={region.cy}
          label={region.label}
          placements={placements}
          allItems={allItems}
          showFeedback={showFeedback}
          correctItemIds={correctItemIds}
        />
      ))}
    </div>
  );
}

function VennDropRegion({
  id, cx, cy, label, placements, allItems, showFeedback, correctItemIds,
}: {
  id: string; cx: number; cy: number; label: string;
  placements: Record<string, string | null>;
  allItems: SortingItem[];
  showFeedback: boolean;
  correctItemIds: Set<string>;
}) {
  const { isOver, setNodeRef } = useDroppable({ id });

  const placed = Object.entries(placements)
    .filter(([, catId]) => catId === id.replace('cat-', ''))
    .map(([itemId]) => allItems.find(i => i.id === itemId))
    .filter(Boolean) as SortingItem[];

  return (
    <div
      ref={setNodeRef}
      className={`absolute w-24 flex flex-col items-center gap-0.5 ${isOver ? 'scale-110' : ''} transition-transform`}
      style={{
        left: `${(cx / 500) * 100}%`,
        top: `${(cy / 400) * 100}%`,
        transform: 'translate(-50%, -50%)',
      }}
    >
      {placed.map(item => (
        <span
          key={item.id}
          className={`text-[10px] px-1.5 py-0.5 rounded ${
            showFeedback && correctItemIds.has(item.id)
              ? 'bg-green-100 text-green-800'
              : showFeedback ? 'bg-red-100 text-red-800'
              : 'bg-white/80 text-gray-700'
          } shadow-sm truncate max-w-full`}
        >
          {item.content}
        </span>
      ))}
      {placed.length === 0 && (
        <span className="text-[10px] text-gray-400 italic">{label}</span>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main Component
// ---------------------------------------------------------------------------

export default function EnhancedSortingCategories({
  items: allItems,
  categories,
  config,
  storeProgress,
  onAction,
}: EnhancedSortingProps) {
  const sortMode: SortMode = config?.sort_mode || 'bucket';
  const cardType: ItemCardType = (config?.item_card_type as ItemCardType) || 'text_only';
  const submitMode = config?.submit_mode || 'batch_submit';
  const instructions = config?.instructions || 'Sort the items into the correct categories.';

  // Layer 3: Initialize from storeProgress for restoration
  const [placements, setPlacements] = useState<Record<string, string | null>>(
    () => storeProgress?.itemCategories
      ? { ...Object.fromEntries(allItems.map(i => [i.id, null])), ...storeProgress.itemCategories }
      : Object.fromEntries(allItems.map(i => [i.id, null]))
  );
  const [isSubmitted, setIsSubmitted] = useState(storeProgress?.isSubmitted ?? false);

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 5 } }),
    useSensor(KeyboardSensor),
  );

  const [activeId, setActiveId] = useState<string | null>(null);

  const unsortedItems = useMemo(
    () => allItems.filter(i => !placements[i.id]),
    [allItems, placements]
  );

  // Correct item IDs per category
  const correctItemIds = useMemo(() => {
    const set = new Set<string>();
    allItems.forEach(item => {
      const correctCats = item.correct_category_ids?.length ? item.correct_category_ids : [item.correctCategoryId];
      const placed = placements[item.id];
      if (placed && correctCats.includes(placed)) {
        set.add(item.id);
      }
    });
    return set;
  }, [allItems, placements]);

  const handleDragStart = useCallback((event: DragStartEvent) => {
    setActiveId(event.active.id as string);
  }, []);

  const handleDragEnd = useCallback((event: DragEndEvent) => {
    setActiveId(null);
    const { active, over } = event;
    if (!over) return;

    const itemId = active.id as string;
    const targetId = (over.id as string).replace('cat-', '').replace(/^overlap-/, '');

    // Check if dropped back into unsorted pool
    if ((over.id as string) === 'unsorted-pool') {
      setPlacements(prev => ({ ...prev, [itemId]: null }));
      onAction({ type: 'unsort', mechanic: 'sorting_categories', itemId });
      return;
    }

    // Check if it's a valid category
    const isCategory = categories.some(c => c.id === targetId) || (over.id as string).startsWith('cat-');
    if (isCategory) {
      const catId = targetId;
      setPlacements(prev => ({ ...prev, [itemId]: catId }));
      onAction({ type: 'sort', mechanic: 'sorting_categories', itemId, categoryId: catId });
    }
  }, [categories, onAction]);

  const handleSubmit = useCallback(() => {
    // Emit unified action — store handles scoring
    onAction({ type: 'submit_sorting', mechanic: 'sorting_categories' });
    setIsSubmitted(true);
  }, [onAction]);

  const handleReset = useCallback(() => {
    setPlacements(Object.fromEntries(allItems.map(i => [i.id, null])));
    setIsSubmitted(false);
  }, [allItems]);

  const activeItem = activeId ? allItems.find(i => i.id === activeId) : null;
  const allPlaced = unsortedItems.length === 0;

  return (
    <div className="w-full max-w-4xl mx-auto">
      {/* Instructions */}
      <div className="mb-5 p-3 bg-pink-50 dark:bg-pink-900/20 rounded-xl border border-pink-200 dark:border-pink-800">
        <p className="text-sm text-pink-800 dark:text-pink-200 font-medium">{instructions}</p>
      </div>

      <DndContext
        sensors={sensors}
        collisionDetection={closestCenter}
        onDragStart={handleDragStart}
        onDragEnd={handleDragEnd}
      >
        {/* Unsorted items pool */}
        {unsortedItems.length > 0 && (
          <div className="mb-5 p-4 bg-gray-50 dark:bg-gray-800/50 rounded-xl border border-gray-200 dark:border-gray-700">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold text-gray-600 dark:text-gray-300">Items to sort:</h3>
              <span className="text-xs px-2 py-0.5 rounded-full bg-gray-200 dark:bg-gray-600 text-gray-600 dark:text-gray-300 font-medium">
                {unsortedItems.length} remaining
              </span>
            </div>
            <div className="flex flex-wrap gap-2">
              {unsortedItems.map(item => (
                <DraggableSortItem
                  key={item.id}
                  item={item}
                  cardType={cardType}
                  isDragging={activeId === item.id}
                  hideDifficulty
                />
              ))}
            </div>
          </div>
        )}

        {/* Category containers */}
        {sortMode === 'venn_2' && categories.length >= 2 ? (
          <VennDiagram2
            categories={categories.slice(0, 2)}
            placements={placements}
            allItems={allItems}
            showFeedback={isSubmitted}
            correctItemIds={correctItemIds}
          />
        ) : (
          /* Bucket / Column grid */
          <div className={`grid gap-4 ${
            categories.length <= 2 ? 'grid-cols-2' :
            categories.length <= 3 ? 'grid-cols-3' :
            'grid-cols-2 md:grid-cols-4'
          }`}>
            {categories.map((cat, idx) => (
              <BucketDropTarget
                key={cat.id}
                category={cat}
                color={getCategoryColor(cat, idx)}
                items={Object.entries(placements)
                  .filter(([, catId]) => catId === cat.id)
                  .map(([itemId]) => itemId)}
                allItems={allItems}
                showFeedback={isSubmitted}
                correctItemIds={correctItemIds}
              />
            ))}
          </div>
        )}

        {/* Drag overlay */}
        <DragOverlay>
          {activeItem && (
            <div className="px-3 py-2 bg-white dark:bg-gray-700 rounded-lg border-2 border-indigo-400 shadow-xl text-sm font-medium text-gray-800 dark:text-gray-100 rotate-2">
              {activeItem.content}
            </div>
          )}
        </DragOverlay>
      </DndContext>

      {/* Results bar */}
      {isSubmitted && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className={`mt-5 p-4 rounded-xl border ${
            correctItemIds.size === allItems.length
              ? 'bg-green-50 dark:bg-green-900/20 border-green-300 dark:border-green-700'
              : 'bg-amber-50 dark:bg-amber-900/20 border-amber-300 dark:border-amber-700'
          }`}
        >
          <p className="font-semibold text-gray-800 dark:text-gray-100">
            {correctItemIds.size === allItems.length
              ? '🎉 All items sorted correctly!'
              : `${correctItemIds.size} of ${allItems.length} items in the correct category.`}
          </p>
        </motion.div>
      )}

      {/* Actions */}
      <div className="mt-5 flex gap-3">
        {!isSubmitted ? (
          <button
            onClick={handleSubmit}
            disabled={!allPlaced}
            className={`flex-1 py-2.5 px-6 rounded-xl font-medium shadow-sm transition-colors ${
              allPlaced
                ? 'bg-pink-600 text-white hover:bg-pink-700'
                : 'bg-gray-300 text-gray-500 cursor-not-allowed'
            }`}
          >
            Check Sorting
          </button>
        ) : (
          <button
            onClick={handleReset}
            className="flex-1 py-2.5 px-6 bg-gray-600 text-white rounded-xl hover:bg-gray-700 transition-colors font-medium shadow-sm"
          >
            Try Again
          </button>
        )}
      </div>
    </div>
  );
}
