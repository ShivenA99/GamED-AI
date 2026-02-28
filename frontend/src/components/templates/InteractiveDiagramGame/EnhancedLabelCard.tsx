'use client';

import { useMemo } from 'react';
import { useDraggable } from '@dnd-kit/core';
import { CSS } from '@dnd-kit/utilities';
import { motion, AnimatePresence } from 'framer-motion';
import { LabelCardStyle } from './types';

export type LabelCardState =
  | 'idle'
  | 'hover'
  | 'grabbed'
  | 'dragging'
  | 'placed'
  | 'incorrect'
  | 'disabled';

interface EnhancedLabelCardProps {
  id: string;
  text: string;
  /** Card display style */
  cardStyle?: LabelCardStyle;
  /** Icon emoji or identifier */
  icon?: string;
  /** Thumbnail image URL */
  thumbnailUrl?: string;
  /** Description text (for text_with_description style) */
  description?: string;
  /** Category for grouping (shown as accent color) */
  category?: string;
  /** Category color override */
  categoryColor?: string;
  /** Whether this label is a distractor */
  isDistractor?: boolean;
  /** External state override */
  state?: LabelCardState;
  /** Whether currently being dragged */
  isDragging?: boolean;
  /** Whether this label was incorrectly placed */
  isIncorrect?: boolean;
  /** Whether this card is disabled (e.g., already placed) */
  isDisabled?: boolean;
  /** Whether this card is selected (for click-to-place mode) */
  isSelected?: boolean;
  /** Incorrect animation style */
  incorrectAnimation?: 'shake' | 'bounce_back' | 'fade_out';
  /** Spring physics config for placement */
  springStiffness?: number;
  springDamping?: number;
  /** Click handler for click-to-place mode */
  onClick?: (id: string) => void;
}

const CATEGORY_COLORS: Record<string, string> = {
  anatomy: '#ef4444',
  process: '#3b82f6',
  function: '#10b981',
  structure: '#8b5cf6',
  default: '#6366f1',
};

function getCategoryColor(category?: string, override?: string): string {
  if (override) return override;
  if (!category) return CATEGORY_COLORS.default;
  return CATEGORY_COLORS[category.toLowerCase()] || CATEGORY_COLORS.default;
}

/** Compute visual state from props */
function computeState(props: EnhancedLabelCardProps): LabelCardState {
  if (props.state) return props.state;
  if (props.isDisabled) return 'disabled';
  if (props.isIncorrect) return 'incorrect';
  if (props.isDragging) return 'dragging';
  return 'idle';
}

/** Get animation variants for incorrect placement */
function getIncorrectVariants(animation: string) {
  switch (animation) {
    case 'shake':
      return {
        animate: {
          x: [0, -8, 8, -6, 6, -3, 3, 0],
          transition: { duration: 0.5 },
        },
      };
    case 'bounce_back':
      return {
        animate: {
          scale: [1, 0.9, 1.05, 0.95, 1],
          transition: { duration: 0.4, type: 'spring' as const, stiffness: 300 },
        },
      };
    case 'fade_out':
      return {
        animate: {
          opacity: [1, 0.3, 1],
          transition: { duration: 0.6 },
        },
      };
    default:
      return { animate: {} };
  }
}

export default function EnhancedLabelCard(props: EnhancedLabelCardProps) {
  const {
    id,
    text,
    cardStyle = 'text',
    icon,
    thumbnailUrl,
    description,
    category,
    categoryColor,
    isDistractor = false,
    isDragging = false,
    isIncorrect = false,
    isDisabled = false,
    isSelected = false,
    incorrectAnimation = 'shake',
    onClick,
  } = props;

  const { attributes, listeners, setNodeRef, transform } = useDraggable({
    id,
    disabled: isDisabled,
  });

  const cardState = computeState(props);
  const accentColor = getCategoryColor(category, categoryColor);

  const style = useMemo(() => ({
    transform: CSS.Translate.toString(transform),
    opacity: isDragging ? 0.6 : 1,
    '--accent-color': accentColor,
  } as React.CSSProperties), [transform, isDragging, accentColor]);

  const incorrectVariants = useMemo(
    () => getIncorrectVariants(incorrectAnimation),
    [incorrectAnimation]
  );

  // State-based classes
  const stateClasses = useMemo(() => {
    const base = 'relative rounded-lg font-medium text-sm shadow-md select-none transition-shadow duration-200';

    switch (cardState) {
      case 'idle':
        return `${base} bg-white dark:bg-gray-700 border-2 border-gray-200 dark:border-gray-600 text-gray-800 dark:text-gray-100 hover:border-indigo-400 hover:shadow-lg cursor-grab`;
      case 'hover':
        return `${base} bg-white dark:bg-gray-700 border-2 border-indigo-400 dark:border-indigo-500 text-gray-800 dark:text-gray-100 shadow-lg cursor-grab`;
      case 'grabbed':
        return `${base} bg-indigo-50 dark:bg-indigo-900/30 border-2 border-indigo-500 text-gray-800 dark:text-gray-100 shadow-xl cursor-grabbing scale-105`;
      case 'dragging':
        return `${base} bg-indigo-50 dark:bg-indigo-900/30 border-2 border-indigo-500 text-gray-800 dark:text-gray-100 shadow-2xl cursor-grabbing scale-105 rotate-1`;
      case 'placed':
        return `${base} bg-green-50 dark:bg-green-900/30 border-2 border-green-400 text-green-800 dark:text-green-200`;
      case 'incorrect':
        return `${base} bg-red-50 dark:bg-red-900/30 border-2 border-red-400 text-red-800 dark:text-red-200`;
      case 'disabled':
        return `${base} bg-gray-100 dark:bg-gray-800 border-2 border-gray-300 dark:border-gray-600 text-gray-400 dark:text-gray-500 opacity-50 cursor-not-allowed`;
      default:
        return base;
    }
  }, [cardState]);

  const handleClick = () => {
    if (onClick && !isDisabled) {
      onClick(id);
    }
  };

  const cardContent = (
    <div
      ref={setNodeRef}
      style={style}
      {...(isDisabled ? {} : listeners)}
      {...attributes}
      className={`${stateClasses} ${isSelected ? 'ring-2 ring-indigo-500 ring-offset-2' : ''}`}
      onClick={handleClick}
      role={onClick ? 'button' : undefined}
      aria-selected={isSelected}
      aria-disabled={isDisabled}
    >
      {/* Category accent bar */}
      {category && (
        <div
          className="absolute top-0 left-0 right-0 h-1 rounded-t-lg"
          style={{ backgroundColor: accentColor }}
        />
      )}

      {/* Card content based on style */}
      <div className={`flex items-center gap-3 ${category ? 'pt-2' : ''} px-3 py-2`}>
        {/* Icon (for text_with_icon style) */}
        {(cardStyle === 'text_with_icon' && icon) && (
          <span className="text-xl flex-shrink-0" aria-hidden="true">
            {icon}
          </span>
        )}

        {/* Thumbnail (for text_with_thumbnail style) */}
        {(cardStyle === 'text_with_thumbnail' && thumbnailUrl) && (
          <div className="w-10 h-10 flex-shrink-0 rounded overflow-hidden bg-gray-100 dark:bg-gray-600">
            <img
              src={thumbnailUrl}
              alt=""
              className="w-full h-full object-cover"
            />
          </div>
        )}

        {/* Text content */}
        <div className="flex-1 min-w-0">
          <span className="block truncate">{text}</span>

          {/* Description (for text_with_description style) */}
          {cardStyle === 'text_with_description' && description && (
            <span className="block text-xs text-gray-500 dark:text-gray-400 mt-0.5 truncate">
              {description}
            </span>
          )}
        </div>

        {/* Distractor indicator (subtle) */}
        {isDistractor && cardState === 'incorrect' && (
          <span className="text-xs text-red-500 dark:text-red-400 flex-shrink-0">
            ✕
          </span>
        )}
      </div>
    </div>
  );

  // Wrap in motion div for animations
  if (isIncorrect) {
    return (
      <motion.div
        {...incorrectVariants}
        key={`incorrect-${id}`}
      >
        {cardContent}
      </motion.div>
    );
  }

  return cardContent;
}

/** Animated placement wrapper: spring physics for snapping into place */
export function AnimatedPlacement({
  children,
  isPlaced,
  targetX,
  targetY,
  springStiffness = 300,
  springDamping = 25,
}: {
  children: React.ReactNode;
  isPlaced: boolean;
  targetX?: number;
  targetY?: number;
  springStiffness?: number;
  springDamping?: number;
}) {
  return (
    <AnimatePresence>
      {isPlaced && targetX !== undefined && targetY !== undefined ? (
        <motion.div
          initial={{ scale: 0.8, opacity: 0 }}
          animate={{
            scale: 1,
            opacity: 1,
            x: targetX,
            y: targetY,
          }}
          exit={{ scale: 0.5, opacity: 0 }}
          transition={{
            type: 'spring',
            stiffness: springStiffness,
            damping: springDamping,
          }}
        >
          {children}
        </motion.div>
      ) : (
        children
      )}
    </AnimatePresence>
  );
}

/** Placement particle burst effect */
export function PlacementParticles({
  x,
  y,
  color = '#22c55e',
  show,
}: {
  x: number;
  y: number;
  color?: string;
  show: boolean;
}) {
  if (!show) return null;

  const particles = Array.from({ length: 8 }, (_, i) => {
    const angle = (i / 8) * Math.PI * 2;
    const distance = 20 + Math.random() * 15;
    return {
      id: i,
      targetX: Math.cos(angle) * distance,
      targetY: Math.sin(angle) * distance,
    };
  });

  return (
    <div
      className="absolute pointer-events-none"
      style={{ left: x, top: y, zIndex: 100 }}
    >
      {particles.map((p) => (
        <motion.div
          key={p.id}
          className="absolute w-2 h-2 rounded-full"
          style={{ backgroundColor: color }}
          initial={{ scale: 1, opacity: 1, x: 0, y: 0 }}
          animate={{
            scale: 0,
            opacity: 0,
            x: p.targetX,
            y: p.targetY,
          }}
          transition={{ duration: 0.6, ease: 'easeOut' }}
        />
      ))}
    </div>
  );
}
