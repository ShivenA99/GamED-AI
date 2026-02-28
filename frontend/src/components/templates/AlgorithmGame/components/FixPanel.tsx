'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { FixOption, FixMode, TestExecutionResult } from '../types';
import CodeFixEditor from './CodeFixEditor';

interface FixPanelProps {
  buggyLineText?: string;
  buggyLinesText?: string[];
  lineNumber?: number;
  bugLines?: number[];
  fixOptions?: FixOption[];
  fixMode: FixMode;
  onSubmit: (fixId: string) => void;
  onRunTests?: (code: string) => void;
  feedbackMessage: string | null;
  feedbackType: 'success' | 'error' | null;
  testResults?: TestExecutionResult[];
  showTestResults?: boolean;
  executionPending?: boolean;
  disabled?: boolean;
  theme?: 'dark' | 'light';
}

export default function FixPanel({
  buggyLineText,
  buggyLinesText,
  lineNumber,
  bugLines,
  fixOptions,
  fixMode,
  onSubmit,
  onRunTests,
  feedbackMessage,
  feedbackType,
  testResults = [],
  showTestResults = false,
  executionPending = false,
  disabled = false,
  theme = 'dark',
}: FixPanelProps) {
  // Normalize to arrays
  const effectiveBuggyLinesText = buggyLinesText ?? (buggyLineText ? [buggyLineText] : []);
  const effectiveBugLines = bugLines ?? (lineNumber != null ? [lineNumber] : []);

  if (fixMode === 'free_text') {
    return (
      <CodeFixEditor
        buggyLinesText={effectiveBuggyLinesText}
        bugLines={effectiveBugLines}
        onRunTests={onRunTests ?? (() => {})}
        testResults={testResults}
        showTestResults={showTestResults}
        executionPending={executionPending}
        feedbackMessage={feedbackMessage}
        feedbackType={feedbackType}
        theme={theme}
      />
    );
  }

  // MCQ mode (existing)
  return (
    <MCQFixPanel
      buggyLineText={effectiveBuggyLinesText[0] ?? ''}
      lineNumber={effectiveBugLines[0] ?? 0}
      fixOptions={fixOptions ?? []}
      onSubmit={onSubmit}
      feedbackMessage={feedbackMessage}
      feedbackType={feedbackType}
      disabled={disabled}
      theme={theme}
    />
  );
}

// Extracted MCQ panel (was the original FixPanel)
function MCQFixPanel({
  buggyLineText,
  lineNumber,
  fixOptions,
  onSubmit,
  feedbackMessage,
  feedbackType,
  disabled = false,
  theme = 'dark',
}: {
  buggyLineText: string;
  lineNumber: number;
  fixOptions: FixOption[];
  onSubmit: (fixId: string) => void;
  feedbackMessage: string | null;
  feedbackType: 'success' | 'error' | null;
  disabled?: boolean;
  theme?: 'dark' | 'light';
}) {
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const isDark = theme === 'dark';

  const handleSubmit = () => {
    if (selectedId && !disabled) {
      onSubmit(selectedId);
      setSelectedId(null);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: 20 }}
      transition={{ type: 'spring', stiffness: 300, damping: 25 }}
      className={`rounded-lg border p-4 ${
        isDark ? 'bg-gray-800 border-gray-600' : 'bg-gray-50 border-gray-200'
      }`}
    >
      {/* Buggy line display */}
      <div className="mb-3">
        <span className={`text-xs uppercase tracking-wide ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>
          Line {lineNumber}
        </span>
        <div
          className={`mt-1 font-mono text-sm px-3 py-1.5 rounded ${
            isDark ? 'bg-red-900/20 text-red-300 border border-red-800/50' : 'bg-red-50 text-red-700 border border-red-200'
          }`}
        >
          {buggyLineText}
        </div>
      </div>

      {/* Fix options */}
      <div className="space-y-2 mb-3">
        <span className={`text-xs uppercase tracking-wide ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>
          Choose the correct fix:
        </span>
        {fixOptions.map((opt) => (
          <motion.button
            key={opt.id}
            whileTap={{ scale: 0.98 }}
            onClick={() => !disabled && setSelectedId(opt.id)}
            className={`w-full text-left p-3 rounded-lg border-2 transition-colors font-mono text-sm ${
              selectedId === opt.id
                ? isDark
                  ? 'border-primary-500 bg-primary-500/10'
                  : 'border-primary-500 bg-primary-50'
                : isDark
                ? 'border-gray-700 hover:border-gray-600 bg-gray-900'
                : 'border-gray-200 hover:border-gray-300 bg-white'
            } ${disabled ? 'opacity-60 cursor-not-allowed' : 'cursor-pointer'}`}
          >
            <div className="flex items-center gap-2">
              <div
                className={`w-4 h-4 rounded-full border-2 flex-shrink-0 ${
                  selectedId === opt.id
                    ? 'border-primary-500 bg-primary-500'
                    : isDark
                    ? 'border-gray-600'
                    : 'border-gray-300'
                }`}
              >
                {selectedId === opt.id && (
                  <div className="w-full h-full rounded-full flex items-center justify-center">
                    <div className="w-1.5 h-1.5 rounded-full bg-white" />
                  </div>
                )}
              </div>
              <span className={isDark ? 'text-gray-200' : 'text-gray-800'}>
                {opt.codeText}
              </span>
            </div>
          </motion.button>
        ))}
      </div>

      {/* Feedback message */}
      <AnimatePresence>
        {feedbackMessage && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className={`mb-3 p-3 rounded-lg text-sm ${
              feedbackType === 'success'
                ? isDark
                  ? 'bg-green-900/20 text-green-300 border border-green-800/50'
                  : 'bg-green-50 text-green-700 border border-green-200'
                : isDark
                ? 'bg-red-900/20 text-red-300 border border-red-800/50'
                : 'bg-red-50 text-red-700 border border-red-200'
            }`}
          >
            {feedbackMessage}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Submit button */}
      <motion.button
        whileHover={!disabled && selectedId ? { scale: 1.02 } : {}}
        whileTap={!disabled && selectedId ? { scale: 0.98 } : {}}
        onClick={handleSubmit}
        disabled={!selectedId || disabled}
        className={`w-full py-2.5 rounded-lg font-medium text-sm transition-colors ${
          selectedId && !disabled
            ? 'bg-primary-500 text-white hover:bg-primary-600'
            : isDark
            ? 'bg-gray-700 text-gray-500 cursor-not-allowed'
            : 'bg-gray-200 text-gray-400 cursor-not-allowed'
        }`}
      >
        Apply Fix
      </motion.button>
    </motion.div>
  );
}
