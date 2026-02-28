'use client';

import { motion } from 'framer-motion';
import {
  BoardRendererProps,
  ItemSelectionBoardConfig,
} from '../constraintPuzzleTypes';
import ConstraintFeedbackBar, { findBarConstraint } from '../ConstraintFeedbackBar';

export default function ItemSelectionBoard({
  config,
  state,
  dispatch,
  constraintResults,
  disabled = false,
  theme = 'dark',
}: BoardRendererProps) {
  const isDark = theme === 'dark';
  const cfg = config as ItemSelectionBoardConfig;
  const columns = cfg.displayColumns ?? Object.keys(cfg.items[0]?.properties ?? {});
  const labels = cfg.propertyLabels ?? {};
  const isGrid = (cfg.layout ?? 'grid') === 'grid';

  // Find capacity/target bar constraint for display
  const barResult = findBarConstraint(constraintResults);

  // Compute summary values for bar display
  const selectedItems = cfg.items.filter((it) => state.selectedIds.includes(it.id));
  const summaries = columns.map((col) => ({
    key: col,
    label: labels[col] ?? col,
    total: selectedItems.reduce((s, it) => s + (Number(it.properties[col]) || 0), 0),
  }));

  return (
    <div className="space-y-4">
      {/* Progress bar(s) */}
      {barResult && barResult.currentValue != null && barResult.targetValue != null && (
        <ConstraintFeedbackBar
          label={
            barResult.constraint.type === 'capacity'
              ? (barResult.constraint.label ?? barResult.constraint.property)
              : 'Progress'
          }
          current={barResult.currentValue}
          max={barResult.targetValue}
          theme={theme}
          rightLabel={
            summaries.length > 1
              ? `${summaries.map((s) => `${s.label}: ${s.total}`).join(' | ')}`
              : undefined
          }
        />
      )}

      {/* Summary line when no bar */}
      {!barResult && summaries.length > 0 && (
        <div className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
          Selected: {state.selectedIds.length} | {summaries.map((s) => `${s.label}: ${s.total}`).join(' | ')}
        </div>
      )}

      {/* Items */}
      <div className={isGrid ? 'grid grid-cols-2 sm:grid-cols-3 gap-3' : 'space-y-2'}>
        {cfg.items.map((item) => {
          const isSelected = state.selectedIds.includes(item.id);
          return (
            <motion.button
              key={item.id}
              whileHover={{ scale: disabled ? 1 : 1.02 }}
              whileTap={{ scale: disabled ? 1 : 0.98 }}
              onClick={() => !disabled && dispatch({ type: 'TOGGLE', id: item.id })}
              disabled={disabled}
              className={`${isGrid ? 'p-3' : 'p-3 w-full'} rounded-lg border-2 text-left transition-all ${
                isSelected
                  ? isDark
                    ? 'border-blue-500 bg-blue-900/30'
                    : 'border-blue-500 bg-blue-50'
                  : isDark
                    ? 'border-gray-600 bg-gray-800 hover:border-gray-500'
                    : 'border-gray-200 bg-white hover:border-gray-400'
              } ${disabled ? 'cursor-default opacity-70' : 'cursor-pointer'}`}
            >
              {item.icon && <div className="text-2xl mb-1">{item.icon}</div>}
              <div className={`text-sm font-medium ${isDark ? 'text-gray-200' : 'text-gray-800'}`}>
                {item.label}
              </div>
              <div className={`text-xs mt-1 flex gap-3 ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
                {columns.map((col) => (
                  <span key={col}>
                    {(labels[col] ?? col).charAt(0).toUpperCase()}: {item.properties[col]}
                  </span>
                ))}
              </div>
              {isSelected && (
                <div className={`text-xs mt-1 font-medium ${isDark ? 'text-blue-400' : 'text-blue-600'}`}>
                  Selected
                </div>
              )}
            </motion.button>
          );
        })}
      </div>
    </div>
  );
}
