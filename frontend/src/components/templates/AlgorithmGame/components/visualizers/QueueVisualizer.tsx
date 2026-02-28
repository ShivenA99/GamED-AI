'use client';

import { motion, AnimatePresence } from 'framer-motion';
import { QueueDataStructure, QueueItemState } from '../../types';

interface QueueVisualizerProps {
  dataStructure: QueueDataStructure;
  theme?: 'dark' | 'light';
}

function getItemBg(state: QueueItemState | undefined, isHighlighted: boolean, theme: string): string {
  const isDark = theme === 'dark';

  if (isHighlighted) {
    return isDark ? 'bg-yellow-500/20 border-yellow-400' : 'bg-yellow-100 border-yellow-500';
  }

  switch (state) {
    case 'enqueuing':
      return isDark ? 'bg-green-500/20 border-green-400' : 'bg-green-100 border-green-500';
    case 'dequeuing':
      return isDark ? 'bg-red-500/20 border-red-400' : 'bg-red-100 border-red-500';
    case 'front':
      return isDark ? 'bg-blue-500/20 border-blue-400' : 'bg-blue-100 border-blue-500';
    case 'back':
      return isDark ? 'bg-purple-500/20 border-purple-400' : 'bg-purple-100 border-purple-500';
    case 'active':
      return isDark ? 'bg-emerald-500/20 border-emerald-400' : 'bg-emerald-100 border-emerald-500';
    default:
      return isDark ? 'bg-gray-700 border-gray-600' : 'bg-gray-100 border-gray-300';
  }
}

function getVariantLabel(variant?: string): string {
  switch (variant?.toLowerCase()) {
    case 'deque':
      return 'Deque';
    case 'priority':
      return 'Priority Queue';
    case 'fifo':
    default:
      return 'FIFO Queue';
  }
}

export default function QueueVisualizer({
  dataStructure,
  theme = 'dark',
}: QueueVisualizerProps) {
  const { items, frontIndex, backIndex, capacity, highlights, variant } = dataStructure;
  const isDark = theme === 'dark';
  const highlightSet = new Set(highlights ?? []);

  // Determine effective front/back indices
  const effectiveFront = frontIndex ?? 0;
  const effectiveBack = backIndex ?? Math.max(items.length - 1, 0);

  return (
    <div
      className={`rounded-lg p-4 ${isDark ? 'bg-[#1e1e1e]' : 'bg-gray-50'}`}
    >
      <h4
        className={`text-xs font-semibold mb-3 uppercase tracking-wider ${
          isDark ? 'text-gray-400' : 'text-gray-500'
        }`}
      >
        {getVariantLabel(variant)}
      </h4>

      <div className="flex items-center justify-center">
        {/* Dequeue direction arrow */}
        {items.length > 0 && (
          <motion.div
            className={`flex flex-col items-center mr-3 ${
              isDark ? 'text-red-400' : 'text-red-600'
            }`}
            animate={{ x: [-3, 3, -3] }}
            transition={{ duration: 1.5, repeat: Infinity }}
          >
            <span className="text-xs font-bold">OUT</span>
            <span className="text-lg">&larr;</span>
          </motion.div>
        )}

        {/* Queue container */}
        <div
          className={`flex items-center border-t-2 border-b-2 rounded-lg px-1 py-2 min-h-[60px] gap-1.5 ${
            isDark ? 'border-gray-500' : 'border-gray-400'
          }`}
          style={{ minWidth: items.length === 0 ? 200 : undefined }}
        >
          {/* Left wall (front) */}
          <div
            className={`w-0.5 self-stretch rounded-full ${
              isDark ? 'bg-gray-500' : 'bg-gray-400'
            }`}
          />

          <AnimatePresence mode="popLayout">
            {items.length === 0 ? (
              <motion.div
                key="empty"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className={`text-center px-8 py-3 text-xs italic ${
                  isDark ? 'text-gray-500' : 'text-gray-400'
                }`}
              >
                (empty)
              </motion.div>
            ) : (
              items.map((item, idx) => {
                const isFront = idx === effectiveFront;
                const isBack = idx === effectiveBack;
                const isHighlighted = highlightSet.has(idx);

                // Determine visual state: explicit state overrides positional state
                let effectiveState = item.state;
                if (!effectiveState || effectiveState === 'default') {
                  if (isFront) effectiveState = 'front';
                  else if (isBack) effectiveState = 'back';
                }

                const bg = getItemBg(effectiveState, isHighlighted, theme);

                return (
                  <motion.div
                    key={item.id}
                    layout
                    initial={{ x: 40, opacity: 0 }}
                    animate={{ x: 0, opacity: 1 }}
                    exit={{ x: -40, opacity: 0 }}
                    transition={{ type: 'spring', stiffness: 300, damping: 25 }}
                    className="flex flex-col items-center"
                  >
                    {/* Front/Back label */}
                    {isFront && (
                      <span
                        className={`text-[10px] font-bold mb-0.5 ${
                          isDark ? 'text-blue-400' : 'text-blue-600'
                        }`}
                      >
                        FRONT
                      </span>
                    )}
                    {isBack && !isFront && (
                      <span
                        className={`text-[10px] font-bold mb-0.5 ${
                          isDark ? 'text-purple-400' : 'text-purple-600'
                        }`}
                      >
                        BACK
                      </span>
                    )}
                    {!isFront && !isBack && (
                      <span className="text-[10px] mb-0.5 invisible">-</span>
                    )}

                    <div
                      className={`border-2 rounded px-4 py-2 text-center font-mono font-bold text-sm min-w-[48px] ${bg} ${
                        isDark ? 'text-white' : 'text-gray-900'
                      }`}
                    >
                      {item.value}
                    </div>

                    {/* Index label */}
                    <span
                      className={`text-xs font-mono mt-0.5 ${
                        isDark ? 'text-gray-500' : 'text-gray-400'
                      }`}
                    >
                      [{idx}]
                    </span>
                  </motion.div>
                );
              })
            )}
          </AnimatePresence>

          {/* Right wall (back) */}
          <div
            className={`w-0.5 self-stretch rounded-full ${
              isDark ? 'bg-gray-500' : 'bg-gray-400'
            }`}
          />
        </div>

        {/* Enqueue direction arrow */}
        {items.length > 0 && (
          <motion.div
            className={`flex flex-col items-center ml-3 ${
              isDark ? 'text-green-400' : 'text-green-600'
            }`}
            animate={{ x: [-3, 3, -3] }}
            transition={{ duration: 1.5, repeat: Infinity }}
          >
            <span className="text-xs font-bold">IN</span>
            <span className="text-lg">&rarr;</span>
          </motion.div>
        )}
      </div>

      {/* Capacity bar */}
      {capacity && capacity > 0 && (
        <div className="mt-3 max-w-xs mx-auto">
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

      {/* Legend */}
      <div className="flex items-center justify-center gap-4 mt-3 flex-wrap">
        {[
          { state: 'enqueuing' as const, label: 'Enqueuing' },
          { state: 'dequeuing' as const, label: 'Dequeuing' },
          { state: 'front' as const, label: 'Front' },
          { state: 'back' as const, label: 'Back' },
          { state: 'active' as const, label: 'Active' },
        ]
          .filter((s) =>
            items.some((item) => item.state === s.state) ||
            (s.state === 'front' && items.length > 0) ||
            (s.state === 'back' && items.length > 1),
          )
          .map(({ state, label }) => (
            <div key={state} className="flex items-center gap-1.5">
              <div
                className={`w-3 h-3 rounded-sm border-2 ${getItemBg(state, false, theme)}`}
              />
              <span className={`text-xs ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
                {label}
              </span>
            </div>
          ))}
        {highlightSet.size > 0 && (
          <div className="flex items-center gap-1.5">
            <div
              className={`w-3 h-3 rounded-sm border-2 ${
                isDark ? 'bg-yellow-500/20 border-yellow-400' : 'bg-yellow-100 border-yellow-500'
              }`}
            />
            <span className={`text-xs ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
              Highlighted
            </span>
          </div>
        )}
      </div>
    </div>
  );
}
