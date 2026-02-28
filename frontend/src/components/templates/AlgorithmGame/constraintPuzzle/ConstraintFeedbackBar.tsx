'use client';

import { motion } from 'framer-motion';
import { ConstraintResult } from './constraintPuzzleTypes';

interface ConstraintFeedbackBarProps {
  label: string;
  current: number;
  max: number;
  theme?: 'dark' | 'light';
  /** Additional text shown on the right side */
  rightLabel?: string;
}

export default function ConstraintFeedbackBar({
  label,
  current,
  max,
  theme = 'dark',
  rightLabel,
}: ConstraintFeedbackBarProps) {
  const isDark = theme === 'dark';
  const pct = max > 0 ? Math.min((current / max) * 100, 100) : 0;
  const isOver = current > max;
  const isExact = current === max;

  return (
    <div className={`rounded-lg p-3 ${isDark ? 'bg-gray-800' : 'bg-gray-50'}`}>
      <div className="flex justify-between text-sm mb-2">
        <span className={isDark ? 'text-gray-400' : 'text-gray-500'}>
          {label}: {current}/{max}
        </span>
        {rightLabel && (
          <span
            className={
              isExact
                ? isDark ? 'text-green-400' : 'text-green-600'
                : isDark ? 'text-blue-400' : 'text-blue-600'
            }
          >
            {rightLabel}
          </span>
        )}
      </div>
      <div
        className={`h-3 rounded-full overflow-hidden ${isDark ? 'bg-gray-700' : 'bg-gray-200'}`}
      >
        <motion.div
          className={`h-full rounded-full ${
            isOver
              ? 'bg-red-500'
              : isExact
                ? 'bg-green-500'
                : pct > 80
                  ? 'bg-yellow-500'
                  : 'bg-blue-500'
          }`}
          animate={{ width: `${pct}%` }}
          transition={{ type: 'spring', stiffness: 300, damping: 25 }}
        />
      </div>
    </div>
  );
}

/**
 * Extract the first constraint result that has bar data (currentValue + targetValue).
 */
export function findBarConstraint(
  results: ConstraintResult[],
): ConstraintResult | undefined {
  return results.find(
    (r) =>
      r.currentValue != null &&
      r.targetValue != null &&
      (r.constraint.type === 'capacity' ||
        r.constraint.type === 'exact_target' ||
        r.constraint.type === 'count_exact'),
  );
}
