'use client';

import { motion, AnimatePresence } from 'framer-motion';
import { StackDataStructure, StackItemState } from '../../types';

interface StackVisualizerProps {
  dataStructure: StackDataStructure;
  theme?: 'dark' | 'light';
}

function getItemBg(state: StackItemState, theme: string): string {
  const isDark = theme === 'dark';
  switch (state) {
    case 'pushing':
      return isDark ? 'bg-green-500/20 border-green-400' : 'bg-green-100 border-green-500';
    case 'popping':
      return isDark ? 'bg-red-500/20 border-red-400' : 'bg-red-100 border-red-500';
    case 'top':
      return isDark ? 'bg-blue-500/20 border-blue-400' : 'bg-blue-100 border-blue-500';
    case 'matched':
      return isDark ? 'bg-emerald-500/20 border-emerald-400' : 'bg-emerald-100 border-emerald-500';
    default:
      return isDark ? 'bg-gray-700 border-gray-600' : 'bg-gray-100 border-gray-300';
  }
}

export default function StackVisualizer({
  dataStructure,
  theme = 'dark',
}: StackVisualizerProps) {
  const { items, capacity } = dataStructure;
  const isDark = theme === 'dark';

  // Display items top-to-bottom (last item = top)
  const displayItems = [...items].reverse();

  return (
    <div
      className={`rounded-lg p-4 ${isDark ? 'bg-[#1e1e1e]' : 'bg-gray-50'}`}
    >
      <h4
        className={`text-xs font-semibold mb-3 uppercase tracking-wider ${
          isDark ? 'text-gray-400' : 'text-gray-500'
        }`}
      >
        Stack State
      </h4>

      <div className="flex justify-center">
        <div className="relative">
          {/* TOP indicator */}
          {items.length > 0 && (
            <div className="flex items-center mb-1">
              <motion.span
                className={`text-xs font-bold mr-2 ${
                  isDark ? 'text-blue-400' : 'text-blue-600'
                }`}
                animate={{ x: [0, 4, 0] }}
                transition={{ duration: 1.5, repeat: Infinity }}
              >
                TOP →
              </motion.span>
            </div>
          )}

          {/* Stack container */}
          <div
            className={`border-l-2 border-r-2 border-b-2 rounded-b-lg px-1 pb-1 min-w-[140px] ${
              isDark ? 'border-gray-500' : 'border-gray-400'
            }`}
            style={{ minHeight: items.length === 0 ? 80 : undefined }}
          >
            <AnimatePresence mode="popLayout">
              {items.length === 0 ? (
                <motion.div
                  key="empty"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className={`text-center py-6 text-xs italic ${
                    isDark ? 'text-gray-500' : 'text-gray-400'
                  }`}
                >
                  (empty)
                </motion.div>
              ) : (
                displayItems.map((item, displayIdx) => {
                  const isTop = displayIdx === 0;
                  const bg = getItemBg(
                    isTop && item.state === 'default' ? 'top' : item.state,
                    theme,
                  );

                  return (
                    <motion.div
                      key={item.id}
                      layout
                      initial={{ y: -40, opacity: 0 }}
                      animate={{ y: 0, opacity: 1 }}
                      exit={{ y: -40, opacity: 0 }}
                      transition={{ type: 'spring', stiffness: 300, damping: 25 }}
                      className={`border-2 rounded px-4 py-2 text-center font-mono font-bold text-sm mt-1 ${bg} ${
                        isDark ? 'text-white' : 'text-gray-900'
                      }`}
                    >
                      {item.value}
                      {item.state === 'matched' && (
                        <motion.div
                          className="absolute inset-0 rounded bg-emerald-400/30"
                          initial={{ opacity: 0.8 }}
                          animate={{ opacity: 0 }}
                          transition={{ duration: 0.5 }}
                        />
                      )}
                    </motion.div>
                  );
                })
              )}
            </AnimatePresence>
          </div>

          {/* Capacity bar */}
          {capacity && capacity > 0 && (
            <div className="mt-2">
              <div className="flex justify-between mb-0.5">
                <span
                  className={`text-xs ${
                    isDark ? 'text-gray-500' : 'text-gray-400'
                  }`}
                >
                  {items.length}/{capacity}
                </span>
              </div>
              <div
                className={`h-1.5 rounded-full overflow-hidden ${
                  isDark ? 'bg-gray-700' : 'bg-gray-200'
                }`}
              >
                <motion.div
                  className={`h-full rounded-full ${
                    items.length / capacity > 0.8
                      ? 'bg-red-500'
                      : items.length / capacity > 0.5
                      ? 'bg-yellow-500'
                      : 'bg-green-500'
                  }`}
                  animate={{ width: `${(items.length / capacity) * 100}%` }}
                  transition={{ type: 'spring', stiffness: 200, damping: 20 }}
                />
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Legend */}
      <div className="flex items-center justify-center gap-4 mt-3 flex-wrap">
        {[
          { state: 'pushing' as const, label: 'Pushing' },
          { state: 'popping' as const, label: 'Popping' },
          { state: 'top' as const, label: 'Top' },
          { state: 'matched' as const, label: 'Matched' },
        ]
          .filter((s) =>
            items.some((item) => item.state === s.state) ||
            (s.state === 'top' && items.length > 0),
          )
          .map(({ state, label }) => (
            <div key={state} className="flex items-center gap-1.5">
              <div
                className={`w-3 h-3 rounded-sm border-2 ${getItemBg(state, theme)}`}
              />
              <span className={`text-xs ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
                {label}
              </span>
            </div>
          ))}
      </div>
    </div>
  );
}
