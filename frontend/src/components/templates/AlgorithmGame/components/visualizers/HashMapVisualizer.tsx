'use client';

import { motion, AnimatePresence } from 'framer-motion';
import { useMemo } from 'react';
import { HashMapDataStructure } from '../../types';

interface HashMapVisualizerProps {
  dataStructure: HashMapDataStructure;
  theme?: 'dark' | 'light';
}

function getBucketBg(highlighted: boolean, theme: string): string {
  const isDark = theme === 'dark';
  if (highlighted) {
    return isDark ? 'border-yellow-400 bg-yellow-500/10' : 'border-yellow-500 bg-yellow-50';
  }
  return isDark ? 'border-gray-600 bg-gray-800' : 'border-gray-300 bg-white';
}

function getEntryBg(highlighted: boolean, theme: string): string {
  const isDark = theme === 'dark';
  if (highlighted) {
    return isDark ? 'bg-blue-500/20 border-blue-400' : 'bg-blue-100 border-blue-500';
  }
  return isDark ? 'bg-gray-700 border-gray-600' : 'bg-gray-100 border-gray-300';
}

function formatValue(value: any): string {
  if (value === null || value === undefined) return 'null';
  if (typeof value === 'object') return JSON.stringify(value);
  return String(value);
}

export default function HashMapVisualizer({
  dataStructure,
  theme = 'dark',
}: HashMapVisualizerProps) {
  const { buckets = [], capacity = 0, highlights = [] } = dataStructure;
  const isDark = theme === 'dark';
  // Normalize highlights: can be plain number[] or object[] with {bucket} key
  const highlightSet = useMemo(() => {
    const s = new Set<number>();
    for (const h of highlights) {
      if (typeof h === 'number') s.add(h);
      else if (h && typeof h === 'object' && 'bucket' in h) s.add((h as any).bucket);
    }
    return s;
  }, [highlights]);

  // Total entries count
  const totalEntries = useMemo(
    () => buckets.reduce((sum, bucket) => sum + bucket.length, 0),
    [buckets],
  );

  // Load factor
  const loadFactor = capacity > 0 ? totalEntries / capacity : 0;

  return (
    <div
      className={`rounded-lg p-4 ${isDark ? 'bg-[#1e1e1e]' : 'bg-gray-50'}`}
    >
      <div className="flex items-center justify-between mb-3">
        <h4
          className={`text-xs font-semibold uppercase tracking-wider ${
            isDark ? 'text-gray-400' : 'text-gray-500'
          }`}
        >
          Hash Map
        </h4>
        <span
          className={`text-xs font-mono ${
            isDark ? 'text-gray-500' : 'text-gray-400'
          }`}
        >
          {totalEntries}/{capacity} (load: {(loadFactor * 100).toFixed(0)}%)
        </span>
      </div>

      {/* Buckets */}
      <div className="space-y-1.5 max-h-[320px] overflow-y-auto pr-1">
        <AnimatePresence mode="popLayout">
          {buckets.map((bucket, bucketIdx) => {
            const highlighted = highlightSet.has(bucketIdx);
            const bucketBg = getBucketBg(highlighted, theme);

            return (
              <motion.div
                key={`bucket-${bucketIdx}`}
                layout
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -10 }}
                transition={{ type: 'spring', stiffness: 300, damping: 25, delay: bucketIdx * 0.02 }}
                className={`flex items-stretch border-2 rounded-lg overflow-hidden ${bucketBg}`}
              >
                {/* Bucket index label */}
                <div
                  className={`flex items-center justify-center w-10 shrink-0 font-mono text-xs font-bold border-r-2 ${
                    highlighted
                      ? isDark ? 'border-yellow-400 text-yellow-400' : 'border-yellow-500 text-yellow-700'
                      : isDark ? 'border-gray-600 text-gray-400' : 'border-gray-300 text-gray-500'
                  }`}
                >
                  {bucketIdx}
                </div>

                {/* Entries */}
                <div className="flex items-center gap-1.5 px-2 py-1.5 flex-wrap min-h-[36px] flex-1">
                  {bucket.length === 0 ? (
                    <span
                      className={`text-xs italic ${
                        isDark ? 'text-gray-600' : 'text-gray-400'
                      }`}
                    >
                      empty
                    </span>
                  ) : (
                    <AnimatePresence mode="popLayout">
                      {bucket.map((entry, entryIdx) => (
                        <motion.div
                          key={`${bucketIdx}-${entry.key}`}
                          layout
                          initial={{ opacity: 0, scale: 0.8 }}
                          animate={{ opacity: 1, scale: 1 }}
                          exit={{ opacity: 0, scale: 0.8 }}
                          transition={{ type: 'spring', stiffness: 300, damping: 25 }}
                          className={`inline-flex items-center gap-1 px-2 py-1 rounded border text-xs font-mono ${getEntryBg(highlighted, theme)} ${
                            isDark ? 'text-white' : 'text-gray-900'
                          }`}
                        >
                          <span className={`font-bold ${isDark ? 'text-cyan-400' : 'text-cyan-700'}`}>
                            {entry.key}
                          </span>
                          <span className={isDark ? 'text-gray-500' : 'text-gray-400'}>:</span>
                          <span>{formatValue(entry.value)}</span>

                          {/* Chain arrow between entries in the same bucket */}
                          {entryIdx < bucket.length - 1 && (
                            <motion.span
                              className={`ml-1 ${isDark ? 'text-gray-500' : 'text-gray-400'}`}
                              animate={{ x: [0, 3, 0] }}
                              transition={{ duration: 1.2, repeat: Infinity }}
                            >
                              {'\u2192'}
                            </motion.span>
                          )}
                        </motion.div>
                      ))}
                    </AnimatePresence>
                  )}
                </div>
              </motion.div>
            );
          })}
        </AnimatePresence>
      </div>

      {/* Load factor bar */}
      <div className="mt-3">
        <div
          className={`h-1.5 rounded-full overflow-hidden ${
            isDark ? 'bg-gray-700' : 'bg-gray-200'
          }`}
        >
          <motion.div
            className={`h-full rounded-full ${
              loadFactor > 0.75
                ? 'bg-red-500'
                : loadFactor > 0.5
                ? 'bg-yellow-500'
                : 'bg-green-500'
            }`}
            animate={{ width: `${Math.min(loadFactor * 100, 100)}%` }}
            transition={{ type: 'spring', stiffness: 200, damping: 20 }}
          />
        </div>
      </div>

      {/* Legend */}
      {highlights.length > 0 && (
        <div className="flex items-center justify-center gap-4 mt-3">
          <div className="flex items-center gap-1.5">
            <div
              className={`w-3 h-3 rounded-sm border-2 ${
                isDark ? 'bg-yellow-500/30 border-yellow-400' : 'bg-yellow-200 border-yellow-500'
              }`}
            />
            <span className={`text-xs ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
              Active Bucket
            </span>
          </div>
        </div>
      )}
    </div>
  );
}
