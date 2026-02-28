'use client';

import { motion } from 'framer-motion';
import {
  BoardRendererProps,
  MultisetBuildingBoardConfig,
} from '../constraintPuzzleTypes';
import ConstraintFeedbackBar, { findBarConstraint } from '../ConstraintFeedbackBar';

export default function MultisetBuildingBoard({
  config,
  state,
  dispatch,
  constraintResults,
  disabled = false,
  theme = 'dark',
}: BoardRendererProps) {
  const isDark = theme === 'dark';
  const cfg = config as MultisetBuildingBoardConfig;
  const currentSum = state.bag.reduce((s: number, v) => s + Number(v), 0);

  // Find target bar constraint
  const barResult = findBarConstraint(constraintResults);
  const targetConstraint = constraintResults.find(
    (r) => r.constraint.type === 'exact_target',
  );
  const target = targetConstraint?.targetValue ?? 0;
  const remaining = target - Number(currentSum);

  return (
    <div className="space-y-4">
      {/* Target progress bar */}
      {(cfg.targetDisplay ?? 'progress_bar') !== 'none' && target > 0 && (
        <ConstraintFeedbackBar
          label={cfg.targetLabel ?? 'Total'}
          current={currentSum}
          max={target}
          theme={theme}
          rightLabel={
            remaining === 0
              ? 'Exact match!'
              : remaining > 0
                ? `Remaining: ${remaining}`
                : `Over by ${-remaining}`
          }
        />
      )}

      {/* Available pool */}
      <div>
        <div className={`text-sm font-medium mb-2 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
          Available
        </div>
        <div className="flex flex-wrap gap-3">
          {[...cfg.pool]
            .sort((a, b) => Number(b.value) - Number(a.value))
            .map((item) => (
              <motion.button
                key={item.id}
                whileHover={{ scale: disabled ? 1 : 1.05 }}
                whileTap={{ scale: disabled ? 1 : 0.95 }}
                onClick={() => !disabled && dispatch({ type: 'ADD_TO_BAG', value: item.value })}
                disabled={disabled}
                className={`w-14 h-14 rounded-full border-2 flex items-center justify-center font-bold transition-all ${
                  isDark
                    ? 'border-yellow-600 bg-yellow-900/30 text-yellow-300 hover:bg-yellow-800/40'
                    : 'border-yellow-500 bg-yellow-50 text-yellow-700 hover:bg-yellow-100'
                } ${disabled ? 'cursor-default opacity-70' : 'cursor-pointer'}`}
              >
                {item.icon ?? item.label ?? String(item.value)}
              </motion.button>
            ))}
        </div>
      </div>

      {/* Selected items */}
      <div>
        <div className={`text-sm font-medium mb-2 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
          Your Selection ({state.bag.length} items)
        </div>
        {state.bag.length === 0 ? (
          <div className={`text-sm italic ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>
            Click items above to add them
          </div>
        ) : (
          <div className="flex flex-wrap gap-2">
            {state.bag.map((val, i) => (
              <motion.button
                key={i}
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                whileHover={{ scale: disabled ? 1 : 1.1 }}
                onClick={() => !disabled && dispatch({ type: 'REMOVE_FROM_BAG', index: i })}
                disabled={disabled}
                className={`w-11 h-11 rounded-full border-2 flex items-center justify-center text-sm font-bold transition-all ${
                  isDark
                    ? 'border-blue-600 bg-blue-900/30 text-blue-300 hover:border-red-500 hover:bg-red-900/30'
                    : 'border-blue-500 bg-blue-50 text-blue-700 hover:border-red-500 hover:bg-red-50'
                } ${disabled ? 'cursor-default' : 'cursor-pointer'}`}
                title="Click to remove"
              >
                {String(val)}
              </motion.button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
