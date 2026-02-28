'use client';

import { motion, AnimatePresence } from 'framer-motion';
import { useMemo } from 'react';
import { CustomObjectDataStructure } from '../../types';

interface CustomObjectVisualizerProps {
  dataStructure: CustomObjectDataStructure;
  theme?: 'dark' | 'light';
}

function getFieldBg(highlighted: boolean, theme: string): string {
  const isDark = theme === 'dark';
  if (highlighted) {
    return isDark ? 'bg-yellow-500/15 border-yellow-400' : 'bg-yellow-50 border-yellow-500';
  }
  return isDark ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200';
}

function formatValue(value: any, isDark: boolean): { text: string; colorClass: string; isLong: boolean } {
  if (value === null || value === undefined) {
    return { text: 'null', colorClass: isDark ? 'text-gray-500' : 'text-gray-400', isLong: false };
  }
  if (typeof value === 'boolean') {
    return {
      text: String(value),
      colorClass: value
        ? isDark ? 'text-green-400' : 'text-green-600'
        : isDark ? 'text-red-400' : 'text-red-600',
      isLong: false,
    };
  }
  if (typeof value === 'number') {
    return { text: String(value), colorClass: isDark ? 'text-blue-400' : 'text-blue-600', isLong: false };
  }
  if (typeof value === 'string') {
    return { text: `"${value}"`, colorClass: isDark ? 'text-emerald-400' : 'text-emerald-600', isLong: value.length > 40 };
  }
  if (Array.isArray(value)) {
    const full = JSON.stringify(value, null, 2);
    return { text: full, colorClass: isDark ? 'text-purple-400' : 'text-purple-600', isLong: full.length > 40 };
  }
  if (typeof value === 'object') {
    const full = JSON.stringify(value, null, 2);
    return { text: full, colorClass: isDark ? 'text-orange-400' : 'text-orange-600', isLong: full.length > 40 };
  }
  return { text: String(value), colorClass: isDark ? 'text-gray-300' : 'text-gray-700', isLong: false };
}

export default function CustomObjectVisualizer({
  dataStructure,
  theme = 'dark',
}: CustomObjectVisualizerProps) {
  const isDark = theme === 'dark';

  // Defensive: extract fields from explicit `fields` key, or fall back to
  // all non-meta keys on the data structure itself (handles LLM compound types).
  const fields = useMemo(() => {
    if (dataStructure.fields && typeof dataStructure.fields === 'object') {
      return dataStructure.fields;
    }
    // Fallback: use all keys except meta keys as displayable fields
    const metaKeys = new Set(['type', 'highlights', 'label']);
    const extracted: Record<string, any> = {};
    for (const [k, v] of Object.entries(dataStructure)) {
      if (!metaKeys.has(k)) extracted[k] = v;
    }
    return extracted;
  }, [dataStructure]);

  const highlights = dataStructure.highlights ?? [];
  const label = dataStructure.label;
  const highlightSet = useMemo(() => new Set(highlights), [highlights]);

  const entries = useMemo(() => Object.entries(fields), [fields]);

  return (
    <div
      className={`rounded-lg p-4 ${isDark ? 'bg-[#1e1e1e]' : 'bg-gray-50'}`}
    >
      <h4
        className={`text-xs font-semibold mb-3 uppercase tracking-wider ${
          isDark ? 'text-gray-400' : 'text-gray-500'
        }`}
      >
        {label || 'Object State'}
      </h4>

      {/* Object brace */}
      <div className={`font-mono text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
        <span className="font-bold">{'{'}</span>
      </div>

      {/* Fields */}
      <div className="ml-4 space-y-1 my-1">
        <AnimatePresence mode="popLayout">
          {entries.length === 0 ? (
            <motion.div
              key="empty"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className={`text-xs italic py-2 ${
                isDark ? 'text-gray-500' : 'text-gray-400'
              }`}
            >
              (no fields)
            </motion.div>
          ) : (
            entries.map(([key, value], idx) => {
              const highlighted = highlightSet.has(key);
              const fieldBg = getFieldBg(highlighted, theme);
              const { text, colorClass, isLong } = formatValue(value, isDark);

              return (
                <motion.div
                  key={key}
                  layout
                  initial={{ opacity: 0, x: -8 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: -8 }}
                  transition={{ type: 'spring', stiffness: 300, damping: 25, delay: idx * 0.03 }}
                  className={`px-3 py-1.5 rounded-md border-2 ${fieldBg}`}
                >
                  <div className="flex items-center gap-2">
                    {/* Change indicator dot */}
                    {highlighted && (
                      <motion.div
                        className={`w-2 h-2 rounded-full shrink-0 ${
                          isDark ? 'bg-yellow-400' : 'bg-yellow-500'
                        }`}
                        animate={{ scale: [1, 1.3, 1] }}
                        transition={{ duration: 1, repeat: Infinity }}
                      />
                    )}

                    {/* Key */}
                    <span
                      className={`font-mono text-sm font-bold shrink-0 ${
                        isDark ? 'text-cyan-400' : 'text-cyan-700'
                      }`}
                    >
                      {key}
                    </span>

                    <span
                      className={`font-mono text-sm ${
                        isDark ? 'text-gray-500' : 'text-gray-400'
                      }`}
                    >
                      :
                    </span>

                    {/* Inline value (short) */}
                    {!isLong && (
                      <motion.span
                        className={`font-mono text-sm font-bold truncate ${colorClass}`}
                        animate={highlighted ? { scale: [1, 1.05, 1] } : {}}
                        transition={{ duration: 0.5 }}
                      >
                        {text}
                      </motion.span>
                    )}

                    {/* Trailing comma for short values */}
                    {!isLong && idx < entries.length - 1 && (
                      <span className={`font-mono text-sm ${isDark ? 'text-gray-600' : 'text-gray-400'}`}>
                        ,
                      </span>
                    )}
                  </div>

                  {/* Block value (long / nested objects) */}
                  {isLong && (
                    <pre
                      className={`mt-1 font-mono text-xs overflow-x-auto max-h-24 rounded p-1.5 ${colorClass} ${
                        isDark ? 'bg-gray-900/50' : 'bg-gray-100'
                      }`}
                    >
                      {text}
                    </pre>
                  )}
                </motion.div>
              );
            })
          )}
        </AnimatePresence>
      </div>

      {/* Closing brace */}
      <div className={`font-mono text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
        <span className="font-bold">{'}'}</span>
      </div>

      {/* Legend */}
      {highlights.length > 0 && (
        <div className="flex items-center justify-center gap-4 mt-3">
          <div className="flex items-center gap-1.5">
            <motion.div
              className={`w-2 h-2 rounded-full ${
                isDark ? 'bg-yellow-400' : 'bg-yellow-500'
              }`}
              animate={{ scale: [1, 1.3, 1] }}
              transition={{ duration: 1, repeat: Infinity }}
            />
            <span className={`text-xs ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
              Changed
            </span>
          </div>
        </div>
      )}
    </div>
  );
}
