'use client';

import { motion, AnimatePresence } from 'framer-motion';
import { ArrayDataStructure, ArrayHighlight } from '../../types';

interface ArrayVisualizerProps {
  dataStructure: ArrayDataStructure;
  theme?: 'dark' | 'light';
}

function getHighlightColor(color: ArrayHighlight['color'], theme: string): string {
  const isDark = theme === 'dark';
  const c = String(color).toLowerCase();
  switch (c) {
    case 'comparing':
    case 'yellow':
      return isDark ? 'bg-yellow-500/30 border-yellow-400' : 'bg-yellow-200 border-yellow-500';
    case 'swapping':
    case 'purple':
      return isDark ? 'bg-purple-500/30 border-purple-400' : 'bg-purple-200 border-purple-500';
    case 'sorted':
    case 'green':
      return isDark ? 'bg-green-500/30 border-green-400' : 'bg-green-200 border-green-500';
    case 'active':
    case 'blue':
      return isDark ? 'bg-blue-500/30 border-blue-400' : 'bg-blue-200 border-blue-500';
    case 'success':
    case 'emerald':
    case 'teal':
      return isDark ? 'bg-emerald-500/30 border-emerald-400' : 'bg-emerald-200 border-emerald-500';
    case 'error':
    case 'red':
      return isDark ? 'bg-red-500/30 border-red-400' : 'bg-red-200 border-red-500';
    case 'orange':
      return isDark ? 'bg-orange-500/30 border-orange-400' : 'bg-orange-200 border-orange-500';
    case 'cyan':
      return isDark ? 'bg-cyan-500/30 border-cyan-400' : 'bg-cyan-200 border-cyan-500';
    default:
      return isDark ? 'bg-gray-700 border-gray-600' : 'bg-gray-200 border-gray-300';
  }
}

function getBarColor(highlight: ArrayHighlight | undefined, isSorted: boolean, theme: string): string {
  if (highlight) {
    const c = String(highlight.color).toLowerCase();
    switch (c) {
      case 'comparing':
      case 'yellow': return 'bg-yellow-400';
      case 'swapping':
      case 'purple': return 'bg-purple-400';
      case 'sorted':
      case 'green': return 'bg-green-400';
      case 'success':
      case 'emerald':
      case 'teal': return 'bg-emerald-400';
      case 'error':
      case 'red': return 'bg-red-400';
      case 'active':
      case 'blue': return 'bg-blue-400';
      case 'orange': return 'bg-orange-400';
      case 'cyan': return 'bg-cyan-400';
      default: return 'bg-gray-400';
    }
  }
  if (isSorted) return theme === 'dark' ? 'bg-green-600' : 'bg-green-400';
  return theme === 'dark' ? 'bg-blue-500' : 'bg-blue-400';
}

export default function ArrayVisualizer({
  dataStructure,
  theme = 'dark',
}: ArrayVisualizerProps) {
  const elements = dataStructure.elements ?? [];
  const highlights = dataStructure.highlights ?? [];
  const sortedIndices = dataStructure.sortedIndices ?? [];

  if (elements.length === 0) {
    const isDark = theme === 'dark';
    return (
      <div className={`rounded-lg p-4 text-center ${isDark ? 'bg-[#1e1e1e]' : 'bg-gray-50'}`}>
        <span className={`text-xs italic ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>(empty array)</span>
      </div>
    );
  }

  const maxVal = Math.max(...elements, 1);
  const highlightMap = new Map(highlights.map((h) => [h.index, h]));
  const sortedSet = new Set(sortedIndices);

  return (
    <div
      className={`rounded-lg p-4 ${
        theme === 'dark' ? 'bg-[#1e1e1e]' : 'bg-gray-50'
      }`}
    >
      <h4
        className={`text-xs font-semibold mb-3 uppercase tracking-wider ${
          theme === 'dark' ? 'text-gray-400' : 'text-gray-500'
        }`}
      >
        Array State
      </h4>

      {/* Bar visualization */}
      <div className="flex items-end justify-center gap-2 h-40 mb-3">
        <AnimatePresence mode="popLayout">
          {elements.map((val, idx) => {
            const highlight = highlightMap.get(idx);
            const isSorted = sortedSet.has(idx);
            const heightPercent = (val / maxVal) * 100;
            const barColor = getBarColor(highlight, isSorted, theme);

            return (
              <motion.div
                key={`${idx}-${val}`}
                layout
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                transition={{ type: 'spring', stiffness: 300, damping: 25 }}
                className="flex flex-col items-center flex-1 max-w-[60px]"
              >
                {/* Pointer label above bar */}
                {highlight?.label && (
                  <motion.span
                    initial={{ opacity: 0, y: -5 }}
                    animate={{ opacity: 1, y: 0 }}
                    className={`text-[10px] font-bold mb-0.5 ${getBarColor(highlight, false, theme).replace('bg-', 'text-')}`}
                  >
                    {highlight.label}
                  </motion.span>
                )}
                <motion.div
                  className={`w-full rounded-t-md ${barColor} relative`}
                  animate={{ height: `${heightPercent}%` }}
                  transition={{ type: 'spring', stiffness: 200, damping: 20 }}
                  style={{ minHeight: '20px', height: `${heightPercent}%` }}
                >
                  {highlight?.color === 'swapping' && (
                    <motion.div
                      className="absolute inset-0 rounded-t-md bg-white/20"
                      animate={{ opacity: [0, 0.5, 0] }}
                      transition={{ duration: 0.6, repeat: Infinity }}
                    />
                  )}
                </motion.div>
              </motion.div>
            );
          })}
        </AnimatePresence>
      </div>

      {/* Value labels */}
      <div className="flex justify-center gap-2">
        {elements.map((val, idx) => {
          const highlight = highlightMap.get(idx);
          const isSorted = sortedSet.has(idx);
          const cellColor = highlight
            ? getHighlightColor(highlight.color, theme)
            : isSorted
            ? theme === 'dark'
              ? 'bg-green-900/30 border-green-700'
              : 'bg-green-100 border-green-300'
            : theme === 'dark'
            ? 'bg-gray-800 border-gray-700'
            : 'bg-white border-gray-300';

          return (
            <motion.div
              key={`label-${idx}`}
              layout
              className={`flex-1 max-w-[60px] text-center py-1.5 rounded border-2 font-mono text-sm font-bold ${cellColor} ${
                theme === 'dark' ? 'text-white' : 'text-gray-900'
              }`}
            >
              {val}
            </motion.div>
          );
        })}
      </div>

      {/* Index labels */}
      <div className="flex justify-center gap-2 mt-1">
        {elements.map((_, idx) => (
          <div
            key={`idx-${idx}`}
            className={`flex-1 max-w-[60px] text-center text-xs font-mono ${
              theme === 'dark' ? 'text-gray-500' : 'text-gray-400'
            }`}
          >
            [{idx}]
          </div>
        ))}
      </div>

      {/* Legend */}
      {highlights.length > 0 && (
        <div className="flex items-center justify-center gap-4 mt-3">
          {highlights
            .filter((h, i, arr) => arr.findIndex(x => x.color === h.color) === i)
            .map((h) => (
            <div key={h.color} className="flex items-center gap-1.5">
              <div
                className={`w-3 h-3 rounded-sm ${getBarColor(
                  { index: 0, color: h.color },
                  false,
                  theme,
                )}`}
              />
              <span
                className={`text-xs capitalize ${
                  theme === 'dark' ? 'text-gray-400' : 'text-gray-500'
                }`}
              >
                {h.label || h.color}
              </span>
            </div>
          ))}
          {sortedIndices.length > 0 && (
            <div className="flex items-center gap-1.5">
              <div className={`w-3 h-3 rounded-sm ${theme === 'dark' ? 'bg-green-600' : 'bg-green-400'}`} />
              <span className={`text-xs ${theme === 'dark' ? 'text-gray-400' : 'text-gray-500'}`}>
                sorted
              </span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
