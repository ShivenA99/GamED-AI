'use client';

import { useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { LineState } from '../types';

interface FixedBugDisplay {
  lineNumber: number;
  buggyLineText: string;
  correctLineText: string;
}

interface MultiLineFixedBugDisplay {
  bugLines: number[];
  buggyLinesText: string[];
  correctLinesText: string[];
}

interface ClickableCodePanelProps {
  code: string;
  language: string;
  lineStates: Record<number, LineState>;
  fixedBugs: (FixedBugDisplay | MultiLineFixedBugDisplay)[];
  clickable: boolean;
  onLineClick: (lineNumber: number) => void;
  onLineSelect?: (lineNumber: number, multiSelect: boolean) => void;
  onConfirmSelection?: () => void;
  selectedLine: number | null;
  selectedLines?: number[];
  multiLineMode?: boolean;
  theme?: 'dark' | 'light';
}

function isMultiLineFix(bug: FixedBugDisplay | MultiLineFixedBugDisplay): bug is MultiLineFixedBugDisplay {
  return 'bugLines' in bug && Array.isArray(bug.bugLines);
}

export default function ClickableCodePanel({
  code,
  language,
  lineStates,
  fixedBugs,
  clickable,
  onLineClick,
  onLineSelect,
  onConfirmSelection,
  selectedLine,
  selectedLines = [],
  multiLineMode = false,
  theme = 'dark',
}: ClickableCodePanelProps) {
  const [hoveredLine, setHoveredLine] = useState<number | null>(null);
  const lines = code.split('\n');

  // Build lookup maps for fixed bugs
  const fixedSingleByLine = new Map<number, FixedBugDisplay>();
  const fixedMultiByLine = new Map<number, { bug: MultiLineFixedBugDisplay; indexInBug: number }>();
  const lastLineOfMultiFix = new Set<number>();

  for (const bug of fixedBugs) {
    if (isMultiLineFix(bug)) {
      bug.bugLines.forEach((ln, idx) => {
        fixedMultiByLine.set(ln, { bug, indexInBug: idx });
      });
      if (bug.bugLines.length > 0) {
        lastLineOfMultiFix.add(Math.max(...bug.bugLines));
      }
    } else {
      fixedSingleByLine.set(bug.lineNumber, bug);
    }
  }

  const isLineSelected = useCallback(
    (lineNum: number) => selectedLines.includes(lineNum) || lineNum === selectedLine,
    [selectedLines, selectedLine],
  );

  const isLineInSelectedRange = useCallback(
    (lineNum: number) => {
      if (selectedLines.length < 2) return false;
      const min = Math.min(...selectedLines);
      const max = Math.max(...selectedLines);
      return lineNum >= min && lineNum <= max;
    },
    [selectedLines],
  );

  const getLineBackground = (lineNum: number) => {
    const state = lineStates[lineNum];
    const isDark = theme === 'dark';

    if (state === 'fixed') {
      return isDark ? 'bg-green-900/30' : 'bg-green-50';
    }
    if (isLineSelected(lineNum)) {
      return isDark ? 'bg-yellow-900/40 border-l-2 border-yellow-400' : 'bg-yellow-50 border-l-2 border-yellow-500';
    }
    if (state === 'wrong_click') {
      return isDark ? 'bg-red-900/40' : 'bg-red-50';
    }
    if (hoveredLine === lineNum && clickable) {
      return isDark ? 'bg-gray-700/50' : 'bg-gray-100';
    }
    return '';
  };

  const handleLineClick = useCallback(
    (lineNum: number, event: React.MouseEvent) => {
      if (multiLineMode && onLineSelect) {
        onLineSelect(lineNum, event.shiftKey);
      } else {
        onLineClick(lineNum);
      }
    },
    [multiLineMode, onLineSelect, onLineClick],
  );

  const isDark = theme === 'dark';

  return (
    <div
      className={`rounded-lg overflow-hidden border ${
        isDark ? 'bg-gray-950 border-gray-700' : 'bg-white border-gray-200'
      }`}
    >
      {/* Header */}
      <div
        className={`px-4 py-2 flex items-center justify-between text-xs font-mono ${
          isDark ? 'bg-gray-800 text-gray-400' : 'bg-gray-50 text-gray-500'
        }`}
      >
        <span>{language}</span>
        <div className="flex items-center gap-3">
          {clickable && (
            <span className={isDark ? 'text-yellow-400' : 'text-yellow-600'}>
              {multiLineMode ? 'Click lines to select (Shift+click for range)' : 'Click on the buggy line'}
            </span>
          )}
          {multiLineMode && selectedLines.length > 0 && onConfirmSelection && (
            <motion.button
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              onClick={onConfirmSelection}
              className="px-3 py-1 bg-primary-500 text-white rounded text-xs font-medium hover:bg-primary-600 transition-colors"
            >
              Confirm Selection ({selectedLines.length} line{selectedLines.length !== 1 ? 's' : ''})
            </motion.button>
          )}
        </div>
      </div>

      {/* Code lines */}
      <div className="overflow-x-auto">
        <pre className="text-sm leading-relaxed">
          {lines.map((line, i) => {
            const lineNum = i + 1;
            const singleFixed = fixedSingleByLine.get(lineNum);
            const multiFixed = fixedMultiByLine.get(lineNum);
            const isFixed = lineStates[lineNum] === 'fixed';
            const isClickable = clickable && !isFixed;

            return (
              <div key={lineNum}>
                <motion.div
                  animate={
                    lineStates[lineNum] === 'wrong_click'
                      ? { x: [0, -4, 4, -4, 4, 0] }
                      : lineStates[lineNum] === 'selected'
                      ? { scale: [1, 1.005, 1] }
                      : {}
                  }
                  transition={{ duration: 0.3 }}
                  className={`flex ${getLineBackground(lineNum)} ${
                    isClickable ? 'cursor-pointer' : ''
                  } transition-colors duration-150`}
                  onClick={(e) => isClickable && handleLineClick(lineNum, e)}
                  onMouseEnter={() => setHoveredLine(lineNum)}
                  onMouseLeave={() => setHoveredLine(null)}
                >
                  {/* Line number */}
                  <span
                    className={`select-none w-12 text-right pr-4 flex-shrink-0 ${
                      isLineSelected(lineNum)
                        ? isDark ? 'text-yellow-400' : 'text-yellow-600'
                        : isDark ? 'text-gray-600' : 'text-gray-400'
                    }`}
                  >
                    {lineNum}
                  </span>

                  {/* Code content */}
                  <span
                    className={`flex-1 px-2 py-0.5 font-mono ${
                      isFixed
                        ? 'line-through text-red-400 opacity-60'
                        : isDark
                        ? 'text-gray-200'
                        : 'text-gray-800'
                    }`}
                  >
                    {line || '\u00A0'}
                  </span>
                </motion.div>

                {/* Single-line fixed replacement */}
                <AnimatePresence>
                  {singleFixed && (
                    <motion.div
                      initial={{ opacity: 0, height: 0 }}
                      animate={{ opacity: 1, height: 'auto' }}
                      className={`flex ${isDark ? 'bg-green-900/20' : 'bg-green-50'}`}
                    >
                      <span className="select-none w-12 text-right pr-4 flex-shrink-0 text-green-500">
                        +
                      </span>
                      <span className="flex-1 px-2 py-0.5 font-mono text-green-400 font-medium">
                        {singleFixed.correctLineText}
                      </span>
                    </motion.div>
                  )}
                </AnimatePresence>

                {/* Multi-line fixed replacement: show after the last line of the group */}
                <AnimatePresence>
                  {multiFixed && lastLineOfMultiFix.has(lineNum) && (
                    <motion.div
                      initial={{ opacity: 0, height: 0 }}
                      animate={{ opacity: 1, height: 'auto' }}
                    >
                      {multiFixed.bug.correctLinesText.map((correctLine, idx) => (
                        <div
                          key={idx}
                          className={`flex ${isDark ? 'bg-green-900/20' : 'bg-green-50'}`}
                        >
                          <span className="select-none w-12 text-right pr-4 flex-shrink-0 text-green-500">
                            +
                          </span>
                          <span className="flex-1 px-2 py-0.5 font-mono text-green-400 font-medium">
                            {correctLine}
                          </span>
                        </div>
                      ))}
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            );
          })}
        </pre>
      </div>
    </div>
  );
}
