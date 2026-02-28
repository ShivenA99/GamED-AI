'use client';

import React, { useState, useCallback, useMemo } from 'react';
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  DragEndEvent,
  DragOverlay,
  DragStartEvent,
} from '@dnd-kit/core';
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  useSortable,
  verticalListSortingStrategy,
  horizontalListSortingStrategy,
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { motion, AnimatePresence } from 'framer-motion';
import { SequenceConfigItem, MechanicAction, ActionResult } from '../types';

// Shuffle removed — items arrive in correct order from backend;
// the store/dispatch layer handles initial randomization if needed.

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type LayoutMode = 'horizontal_timeline' | 'vertical_timeline' | 'circular' | 'flowchart' | 'insert_between';
type CardType = 'image_and_text' | 'image_only' | 'text_only' | 'icon_and_text' | 'numbered_text' | 'image_with_caption' | 'text_with_icon';
type ConnectorStyle = 'arrow' | 'dashed_arrow' | 'numbered_circles' | 'chevron' | 'curved_path' | 'none';
type SlotStyle = 'outlined' | 'numbered' | 'shadow' | 'labeled' | 'minimal' | 'glowing';
type InteractionPattern = 'drag_to_reorder' | 'drag_to_slots' | 'insert_between' | 'click_to_place';

export interface SequencingMechanicConfig {
  layout_mode?: LayoutMode;
  interaction_pattern?: InteractionPattern;
  direction?: 'left_to_right' | 'top_to_bottom';
  card_type?: CardType;
  card_size?: 'small' | 'medium' | 'large';
  show_description?: boolean;
  image_aspect_ratio?: '1:1' | '4:3' | '16:9';
  connector_style?: ConnectorStyle;
  animate_connectors?: boolean;
  slot_style?: SlotStyle;
  show_position_numbers?: boolean;
  show_endpoints?: boolean;
  start_label?: string;
  end_label?: string;
  is_cyclic?: boolean;
  instruction_text?: string;
}

export interface EnhancedSequenceBuilderProps {
  items: SequenceConfigItem[];
  correctOrder: string[];
  allowPartialCredit?: boolean;
  config?: SequencingMechanicConfig;
  /** Source-of-truth progress from store. Used for restoring state on mount. */
  storeProgress?: { currentOrder: string[]; isSubmitted: boolean; correctPositions: number; totalPositions: number } | null;
  /** Unified action dispatch — the only output channel. */
  onAction: (action: MechanicAction) => ActionResult | null;
}

interface SequenceResult {
  isCorrect: boolean;
  correctPositions: number;
  totalPositions: number;
}

// ---------------------------------------------------------------------------
// SequenceItemCard — Rich card with image, icon, description
// ---------------------------------------------------------------------------

function SequenceItemCard({
  item,
  cardType = 'text_only',
  cardSize = 'medium',
  showDescription = true,
  isCorrect,
  showFeedback,
  isDragOverlay,
  position,
}: {
  item: SequenceConfigItem;
  cardType?: CardType;
  cardSize?: string;
  showDescription?: boolean;
  isCorrect?: boolean;
  showFeedback: boolean;
  isDragOverlay?: boolean;
  position?: number;
}) {
  const hasImage =
    (cardType === 'image_and_text' || cardType === 'image_only' || cardType === 'image_with_caption') &&
    !!item.image;

  // Image cards get wider min-width and no padding on the image portion
  const sizeClasses = hasImage
    ? { small: 'min-w-[160px]', medium: 'min-w-[200px]', large: 'min-w-[240px]' }[cardSize] || 'min-w-[200px]'
    : { small: 'p-2 min-w-[120px]', medium: 'p-3 min-w-[160px]', large: 'p-4 min-w-[200px]' }[cardSize] || 'p-3 min-w-[160px]';

  const feedbackBorder = showFeedback
    ? isCorrect
      ? 'border-green-400 bg-green-50 dark:bg-green-900/20'
      : 'border-red-400 bg-red-50 dark:bg-red-900/20'
    : 'border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-700';

  return (
    <div
      className={`
        rounded-xl border-2 shadow-sm transition-all duration-200 overflow-hidden
        ${sizeClasses}
        ${feedbackBorder}
        ${isDragOverlay ? 'shadow-2xl scale-105 rotate-2 opacity-90' : ''}
      `}
    >
      {/* Image area — flush to card edges, proper aspect ratio */}
      {hasImage && (
        <div className="bg-gray-50 dark:bg-gray-600">
          <img
            src={item.image}
            alt={item.content}
            className="w-full aspect-[4/3] object-contain"
          />
        </div>
      )}

      {/* Content area (padded) */}
      <div className={hasImage ? 'px-3 py-2' : ''}>
        {/* Icon + text row */}
        <div className="flex items-start gap-2">
          {/* Position number */}
          {position !== undefined && (
            <span className="flex-shrink-0 w-6 h-6 rounded-full bg-indigo-100 dark:bg-indigo-900/40 text-indigo-700 dark:text-indigo-300 text-xs font-bold flex items-center justify-center">
              {position}
            </span>
          )}

          {/* Icon */}
          {(cardType === 'icon_and_text') && item.icon && (
            <span className="text-xl flex-shrink-0">{item.icon}</span>
          )}

          {/* Drag handle */}
          <div className="text-gray-300 dark:text-gray-500 flex-shrink-0 cursor-grab active:cursor-grabbing mt-0.5">
            <svg className="w-4 h-4" viewBox="0 0 24 24" fill="currentColor">
              <circle cx="9" cy="5" r="1.5" /><circle cx="15" cy="5" r="1.5" />
              <circle cx="9" cy="12" r="1.5" /><circle cx="15" cy="12" r="1.5" />
              <circle cx="9" cy="19" r="1.5" /><circle cx="15" cy="19" r="1.5" />
            </svg>
          </div>

          {/* Text content */}
          {cardType !== 'image_only' && (
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-gray-800 dark:text-gray-100 leading-snug">
                {item.content}
              </p>
              {showDescription && item.description && (
                <p className="text-xs text-gray-500 dark:text-gray-400 mt-1 line-clamp-2">
                  {item.description}
                </p>
              )}
            </div>
          )}

          {/* Feedback indicator */}
          {showFeedback && (
            <span className={`flex-shrink-0 text-lg ${isCorrect ? 'text-green-500' : 'text-red-500'}`}>
              {isCorrect ? '✓' : '✗'}
            </span>
          )}
        </div>

        {/* Category accent */}
        {item.category && (
          <div className="mt-2">
            <span className="text-[10px] uppercase tracking-wider text-gray-400 dark:text-gray-500 font-medium">
              {item.category}
            </span>
          </div>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// SortableSequenceCard — Wraps card in dnd-kit sortable
// ---------------------------------------------------------------------------

function SortableSequenceCard({
  item,
  index,
  config,
  isCorrect,
  showFeedback,
}: {
  item: SequenceConfigItem;
  index: number;
  config: SequencingMechanicConfig;
  isCorrect?: boolean;
  showFeedback: boolean;
}) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id: item.id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.4 : 1,
  };

  return (
    <div ref={setNodeRef} style={style} {...attributes} {...listeners}>
      <SequenceItemCard
        item={item}
        cardType={config.card_type}
        cardSize={config.card_size}
        showDescription={config.show_description}
        isCorrect={isCorrect}
        showFeedback={showFeedback}
        position={config.show_position_numbers ? index + 1 : undefined}
      />
    </div>
  );
}

// ---------------------------------------------------------------------------
// SequenceConnector — SVG connector between cards
// ---------------------------------------------------------------------------

function SequenceConnector({
  style = 'arrow',
  direction = 'horizontal',
  animate = true,
  isPlaced = false,
  number,
}: {
  style?: ConnectorStyle;
  direction?: 'horizontal' | 'vertical';
  animate?: boolean;
  isPlaced?: boolean;
  number?: number;
}) {
  if (style === 'none') return null;

  const isHoriz = direction === 'horizontal';
  const size = isHoriz ? 'w-8 h-6' : 'w-6 h-8';

  if (style === 'numbered_circles' && number !== undefined) {
    return (
      <div className={`flex items-center justify-center ${size}`}>
        <motion.div
          initial={animate ? { scale: 0 } : false}
          animate={{ scale: 1 }}
          className="w-5 h-5 rounded-full bg-indigo-500 text-white text-[10px] font-bold flex items-center justify-center"
        >
          {number}
        </motion.div>
      </div>
    );
  }

  const viewBox = isHoriz ? '0 0 32 24' : '0 0 24 32';
  const arrowPath = isHoriz
    ? 'M 4 12 L 24 12 L 20 6 M 24 12 L 20 18'
    : 'M 12 4 L 12 24 L 6 20 M 12 24 L 18 20';

  const dashArray = style === 'dashed_arrow' ? '4 3' : 'none';

  return (
    <div className={`flex items-center justify-center ${size} flex-shrink-0`}>
      <motion.svg
        viewBox={viewBox}
        className="w-full h-full"
        initial={animate && isPlaced ? { opacity: 0, scale: 0.5 } : false}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ type: 'spring', stiffness: 300, damping: 20 }}
      >
        <path
          d={arrowPath}
          fill="none"
          stroke={isPlaced ? '#6366f1' : '#d1d5db'}
          strokeWidth={2}
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeDasharray={dashArray}
        />
      </motion.svg>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Endpoint label (Start / End markers)
// ---------------------------------------------------------------------------

function EndpointLabel({ label, type }: { label: string; type: 'start' | 'end' }) {
  const colors = type === 'start'
    ? 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300 border-green-300 dark:border-green-700'
    : 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300 border-red-300 dark:border-red-700';

  return (
    <div className={`px-3 py-1.5 rounded-full border text-xs font-semibold ${colors} flex-shrink-0`}>
      {label}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main Component
// ---------------------------------------------------------------------------

export default function EnhancedSequenceBuilder({
  items: initialItems,
  correctOrder,
  allowPartialCredit = true,
  config: rawConfig,
  storeProgress,
  onAction,
}: EnhancedSequenceBuilderProps) {
  const config: Required<SequencingMechanicConfig> = useMemo(() => ({
    layout_mode: rawConfig?.layout_mode || 'horizontal_timeline',
    interaction_pattern: rawConfig?.interaction_pattern || 'drag_to_reorder',
    direction: rawConfig?.direction || 'left_to_right',
    card_type: rawConfig?.card_type || 'text_only',
    card_size: rawConfig?.card_size || 'medium',
    show_description: rawConfig?.show_description ?? true,
    image_aspect_ratio: rawConfig?.image_aspect_ratio || '4:3',
    connector_style: rawConfig?.connector_style || 'arrow',
    animate_connectors: rawConfig?.animate_connectors ?? true,
    slot_style: rawConfig?.slot_style || 'outlined',
    show_position_numbers: rawConfig?.show_position_numbers ?? true,
    show_endpoints: rawConfig?.show_endpoints ?? false,
    start_label: rawConfig?.start_label || 'Start',
    end_label: rawConfig?.end_label || 'End',
    is_cyclic: rawConfig?.is_cyclic ?? false,
    instruction_text: rawConfig?.instruction_text || 'Arrange the steps in the correct order.',
  }), [rawConfig]);

  // Filter out distractors
  const validItems = useMemo(
    () => initialItems.filter(i => !i.is_distractor),
    [initialItems]
  );

  const [items, setItems] = useState<SequenceConfigItem[]>(() => {
    // Restore from progress if available, otherwise use natural order
    if (storeProgress?.currentOrder && storeProgress.currentOrder.length > 0) {
      const byId = new Map(validItems.map(i => [i.id, i]));
      const restored = storeProgress.currentOrder
        .map(id => byId.get(id))
        .filter(Boolean) as SequenceConfigItem[];
      if (restored.length === validItems.length) return restored;
    }
    return validItems;
  });
  const [isSubmitted, setIsSubmitted] = useState(false);
  const [result, setResult] = useState<SequenceResult | null>(null);
  const [activeId, setActiveId] = useState<string | null>(null);

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 5 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
  );

  // Force vertical layout when too many items to fit horizontally, or when explicitly vertical
  const horizontalModes: string[] = ['horizontal_timeline', 'circular'];
  const hasImages = config.card_type === 'image_and_text' || config.card_type === 'image_only' || config.card_type === 'image_with_caption';
  const maxHorizontal = hasImages ? 3 : 4;
  const isHorizontal = horizontalModes.includes(config.layout_mode) && items.length <= maxHorizontal;

  const handleDragStart = useCallback((event: DragStartEvent) => {
    setActiveId(event.active.id as string);
  }, []);

  const handleDragEnd = useCallback((event: DragEndEvent) => {
    setActiveId(null);
    const { active, over } = event;
    if (over && active.id !== over.id) {
      let newOrder: string[] | null = null;
      setItems((curr) => {
        const oldIdx = curr.findIndex(i => i.id === active.id);
        const newIdx = curr.findIndex(i => i.id === over.id);
        const next = arrayMove(curr, oldIdx, newIdx);
        newOrder = next.map(i => i.id);
        return next;
      });
      // Dispatch outside setState to avoid updating another component during render
      if (newOrder) {
        onAction({ type: 'reorder', mechanic: 'sequencing', newOrder });
      }
    }
  }, [onAction]);

  const handleSubmit = useCallback(() => {
    // Emit unified action — store handles scoring and completion
    const actionResult = onAction({ type: 'submit_sequence', mechanic: 'sequencing' });

    // Use ActionResult for visual feedback (store is source of truth for score)
    const correctPositions = actionResult?.data?.correctPositions as number ?? 0;
    const totalPositions = actionResult?.data?.totalPositions as number ?? correctOrder.length;

    const r: SequenceResult = {
      isCorrect: actionResult?.isCorrect ?? false,
      correctPositions,
      totalPositions,
    };
    setResult(r);
    setIsSubmitted(true);
  }, [correctOrder, onAction]);

  const handleReset = useCallback(() => {
    setItems(validItems);
    setIsSubmitted(false);
    setResult(null);
  }, [validItems]);

  const getItemCorrectness = useCallback(
    (itemId: string, index: number) => (isSubmitted ? correctOrder[index] === itemId : undefined),
    [isSubmitted, correctOrder]
  );

  const activeItem = activeId ? items.find(i => i.id === activeId) : null;

  // Layout container classes
  const trackClasses = isHorizontal
    ? 'flex flex-row items-center gap-1 overflow-x-auto pb-4 px-2'
    : 'flex flex-col gap-1 px-2';

  return (
    <div className="w-full max-w-4xl mx-auto">
      {/* Instructions */}
      <div className="mb-5 p-3 bg-indigo-50 dark:bg-indigo-900/20 rounded-xl border border-indigo-200 dark:border-indigo-800">
        <p className="text-sm text-indigo-800 dark:text-indigo-200 font-medium">{config.instruction_text}</p>
      </div>

      {/* Progress bar */}
      {isSubmitted && result && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-4"
        >
          <div className="flex items-center justify-between mb-1">
            <span className="text-xs font-medium text-gray-600 dark:text-gray-400">
              {result.correctPositions} of {result.totalPositions} correct
            </span>
            <span className="text-sm font-bold text-indigo-600 dark:text-indigo-400">
              {result.totalPositions > 0 ? Math.round((result.correctPositions / result.totalPositions) * 100) : 0}%
            </span>
          </div>
          <div className="w-full h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
            <motion.div
              className={`h-full rounded-full ${result.isCorrect ? 'bg-green-500' : 'bg-amber-500'}`}
              initial={{ width: 0 }}
              animate={{ width: `${result.totalPositions > 0 ? Math.round((result.correctPositions / result.totalPositions) * 100) : 0}%` }}
              transition={{ duration: 0.8, ease: 'easeOut' }}
            />
          </div>
        </motion.div>
      )}

      {/* Timeline track with cards and connectors */}
      <DndContext
        sensors={sensors}
        collisionDetection={closestCenter}
        onDragStart={handleDragStart}
        onDragEnd={handleDragEnd}
      >
        <SortableContext
          items={items.map(i => i.id)}
          strategy={isHorizontal ? horizontalListSortingStrategy : verticalListSortingStrategy}
          disabled={isSubmitted}
        >
          <div className={`${isHorizontal ? 'relative' : ''}`}>
            {/* Track background line */}
            {isHorizontal && (
              <div className="absolute top-1/2 left-0 right-0 h-0.5 bg-gray-200 dark:bg-gray-600 -translate-y-1/2 z-0" />
            )}
            {!isHorizontal && (
              <div className="absolute top-0 bottom-0 left-6 w-0.5 bg-gray-200 dark:bg-gray-600 z-0" />
            )}

            <div className={trackClasses} style={{ position: 'relative', zIndex: 1 }}>
              {/* Start endpoint */}
              {config.show_endpoints && (
                <EndpointLabel label={config.start_label} type="start" />
              )}

              {items.map((item, index) => (
                <React.Fragment key={item.id}>
                  {/* Connector before card (skip first) */}
                  {index > 0 && (
                    <SequenceConnector
                      style={config.connector_style}
                      direction={isHorizontal ? 'horizontal' : 'vertical'}
                      animate={config.animate_connectors}
                      isPlaced={isSubmitted}
                      number={index}
                    />
                  )}

                  {/* Card */}
                  <SortableSequenceCard
                    item={item}
                    index={index}
                    config={config}
                    isCorrect={getItemCorrectness(item.id, index)}
                    showFeedback={isSubmitted}
                  />
                </React.Fragment>
              ))}

              {/* Cyclic connector back to start */}
              {config.is_cyclic && items.length > 0 && (
                <SequenceConnector
                  style={config.connector_style}
                  direction={isHorizontal ? 'horizontal' : 'vertical'}
                  animate={config.animate_connectors}
                  isPlaced={isSubmitted}
                  number={items.length}
                />
              )}

              {/* End endpoint */}
              {config.show_endpoints && !config.is_cyclic && (
                <EndpointLabel label={config.end_label} type="end" />
              )}
            </div>
          </div>
        </SortableContext>

        {/* Drag overlay */}
        <DragOverlay>
          {activeItem && (
            <SequenceItemCard
              item={activeItem}
              cardType={config.card_type}
              cardSize={config.card_size}
              showDescription={config.show_description}
              showFeedback={false}
              isDragOverlay
            />
          )}
        </DragOverlay>
      </DndContext>

      {/* Result message */}
      <AnimatePresence>
        {isSubmitted && result && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className={`mt-5 p-4 rounded-xl border ${
              result.isCorrect
                ? 'bg-green-50 dark:bg-green-900/20 border-green-300 dark:border-green-700'
                : 'bg-amber-50 dark:bg-amber-900/20 border-amber-300 dark:border-amber-700'
            }`}
          >
            <p className="font-semibold text-gray-800 dark:text-gray-100">
              {result.isCorrect
                ? '🎉 Perfect! All items are in the correct order.'
                : `${result.correctPositions} of ${result.totalPositions} items in the correct position.`}
            </p>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Actions */}
      <div className="mt-5 flex gap-3">
        {!isSubmitted && (
          <button
            onClick={handleSubmit}
            className="flex-1 py-2.5 px-6 bg-indigo-600 text-white rounded-xl hover:bg-indigo-700 transition-colors font-medium shadow-sm"
          >
            Check Order
          </button>
        )}
        {isSubmitted && result && !result.isCorrect && (
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
