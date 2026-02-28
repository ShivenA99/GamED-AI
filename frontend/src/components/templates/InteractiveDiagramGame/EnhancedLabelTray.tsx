'use client';

import { useMemo, useState } from 'react';
import { EnhancedLabel, EnhancedDistractorLabel, TrayLayout, LabelCardStyle } from './types';
import EnhancedLabelCard from './EnhancedLabelCard';

interface EnhancedLabelTrayProps {
  /** Labels available for placement */
  labels: (EnhancedLabel | EnhancedDistractorLabel)[];
  /** Currently dragging label ID */
  draggingLabelId: string | null;
  /** Label that was incorrectly placed (for animation) */
  incorrectLabelId?: string | null;
  /** Tray layout mode */
  layout?: TrayLayout;
  /** Tray position relative to diagram */
  position?: 'bottom' | 'right' | 'left' | 'top';
  /** Whether to show category grouping */
  showCategories?: boolean;
  /** Whether to show remaining count badge */
  showRemaining?: boolean;
  /** Label card style */
  labelStyle?: LabelCardStyle;
  /** Incorrect animation style */
  incorrectAnimation?: 'shake' | 'bounce_back' | 'fade_out';
  /** Click-to-place mode: callback when label is clicked */
  onLabelClick?: (id: string) => void;
  /** Currently selected label ID (for click-to-place) */
  selectedLabelId?: string | null;
  /** Total original label count (for remaining calculation) */
  totalLabels?: number;
}

interface CategoryGroup {
  name: string;
  labels: (EnhancedLabel | EnhancedDistractorLabel)[];
  color?: string;
}

function groupByCategory(labels: (EnhancedLabel | EnhancedDistractorLabel)[]): CategoryGroup[] {
  const groups = new Map<string, CategoryGroup>();
  const uncategorized: (EnhancedLabel | EnhancedDistractorLabel)[] = [];

  for (const label of labels) {
    const cat = (label as EnhancedLabel).category;
    if (cat) {
      if (!groups.has(cat)) {
        groups.set(cat, { name: cat, labels: [], color: undefined });
      }
      groups.get(cat)!.labels.push(label);
    } else {
      uncategorized.push(label);
    }
  }

  const result = Array.from(groups.values());
  if (uncategorized.length > 0) {
    result.push({ name: 'Other', labels: uncategorized });
  }
  return result;
}

function getLayoutClasses(layout: TrayLayout): string {
  switch (layout) {
    case 'horizontal':
      return 'flex flex-row flex-wrap gap-2';
    case 'vertical':
      return 'flex flex-col gap-2';
    case 'grid':
      return 'grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-2';
    case 'grouped':
      return 'flex flex-col gap-4';
    default:
      return 'flex flex-wrap gap-2';
  }
}

function getPositionClasses(position: string): string {
  switch (position) {
    case 'right':
      return 'w-64 max-h-[600px] overflow-y-auto';
    case 'left':
      return 'w-64 max-h-[600px] overflow-y-auto';
    case 'top':
      return 'w-full';
    case 'bottom':
    default:
      return 'w-full';
  }
}

function isEnhancedLabel(label: EnhancedLabel | EnhancedDistractorLabel): label is EnhancedLabel {
  return 'correctZoneId' in label;
}

export default function EnhancedLabelTray({
  labels,
  draggingLabelId,
  incorrectLabelId,
  layout = 'horizontal',
  position = 'bottom',
  showCategories = false,
  showRemaining = true,
  labelStyle = 'text',
  incorrectAnimation = 'shake',
  onLabelClick,
  selectedLabelId,
  totalLabels,
}: EnhancedLabelTrayProps) {
  const [searchQuery, setSearchQuery] = useState('');

  // Filter by search
  const filteredLabels = useMemo(() => {
    if (!searchQuery.trim()) return labels;
    const q = searchQuery.toLowerCase();
    return labels.filter((l) => l.text.toLowerCase().includes(q));
  }, [labels, searchQuery]);

  // Group by category if enabled
  const categoryGroups = useMemo(() => {
    if (!showCategories || layout !== 'grouped') return null;
    return groupByCategory(filteredLabels);
  }, [filteredLabels, showCategories, layout]);

  const remaining = labels.length;
  const total = totalLabels ?? labels.length;

  if (labels.length === 0) {
    return (
      <div className={`p-4 bg-green-50 dark:bg-green-900/20 rounded-xl text-center border border-green-200 dark:border-green-800 ${getPositionClasses(position)}`}>
        <div className="flex items-center justify-center gap-2">
          <svg className="w-5 h-5 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
          <p className="text-green-700 dark:text-green-300 font-medium text-sm">All labels placed!</p>
        </div>
      </div>
    );
  }

  const renderLabel = (label: EnhancedLabel | EnhancedDistractorLabel) => {
    const enhanced = label as EnhancedLabel;
    const isDistractor = !isEnhancedLabel(label);

    return (
      <EnhancedLabelCard
        key={label.id}
        id={label.id}
        text={label.text}
        cardStyle={labelStyle}
        icon={enhanced.icon}
        thumbnailUrl={enhanced.thumbnail_url}
        description={enhanced.description}
        category={enhanced.category}
        isDistractor={isDistractor}
        isDragging={draggingLabelId === label.id}
        isIncorrect={incorrectLabelId === label.id}
        isSelected={selectedLabelId === label.id}
        incorrectAnimation={incorrectAnimation}
        onClick={onLabelClick}
      />
    );
  };

  return (
    <div className={`p-4 bg-gray-50 dark:bg-gray-800/50 rounded-xl border border-gray-200 dark:border-gray-700 ${getPositionClasses(position)}`}>
      {/* Header with remaining count */}
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-gray-600 dark:text-gray-300">
          {onLabelClick ? 'Click a label, then click a zone:' : 'Drag labels to the correct positions:'}
        </h3>
        {showRemaining && (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-indigo-100 dark:bg-indigo-900/40 text-indigo-700 dark:text-indigo-300">
            {remaining} remaining
          </span>
        )}
      </div>

      {/* Search filter (for large label sets) */}
      {labels.length > 8 && (
        <div className="mb-3">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search labels..."
            className="w-full px-3 py-1.5 text-sm rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-800 dark:text-gray-200 focus:outline-none focus:ring-2 focus:ring-indigo-400"
          />
        </div>
      )}

      {/* Category grouped layout */}
      {categoryGroups ? (
        <div className="flex flex-col gap-4">
          {categoryGroups.map((group) => (
            <div key={group.name}>
              <div className="flex items-center gap-2 mb-2">
                <span className="text-xs font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400">
                  {group.name}
                </span>
                <span className="text-xs text-gray-400 dark:text-gray-500">
                  ({group.labels.length})
                </span>
              </div>
              <div className="flex flex-wrap gap-2">
                {group.labels.map(renderLabel)}
              </div>
            </div>
          ))}
        </div>
      ) : (
        /* Standard layout */
        <div className={getLayoutClasses(layout)}>
          {filteredLabels.map(renderLabel)}
        </div>
      )}
    </div>
  );
}
