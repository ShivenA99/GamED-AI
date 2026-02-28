'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { TestExecutionResult } from '../types';

interface CodeFixEditorProps {
  buggyLinesText: string[];
  bugLines: number[];
  onRunTests: (code: string) => void;
  testResults: TestExecutionResult[];
  showTestResults: boolean;
  executionPending: boolean;
  feedbackMessage: string | null;
  feedbackType: 'success' | 'error' | null;
  theme?: 'dark' | 'light';
}

export default function CodeFixEditor({
  buggyLinesText,
  bugLines,
  onRunTests,
  testResults,
  showTestResults,
  executionPending,
  feedbackMessage,
  feedbackType,
  theme = 'dark',
}: CodeFixEditorProps) {
  const [code, setCode] = useState(buggyLinesText.join('\n'));
  const isDark = theme === 'dark';

  const lineLabel =
    bugLines.length === 1
      ? `Line ${bugLines[0]}`
      : `Lines ${Math.min(...bugLines)}-${Math.max(...bugLines)}`;

  const handleRunTests = () => {
    if (!executionPending) {
      onRunTests(code);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    // Cmd/Ctrl+Enter to run tests
    if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
      e.preventDefault();
      handleRunTests();
    }
    // Tab inserts spaces
    if (e.key === 'Tab') {
      e.preventDefault();
      const target = e.target as HTMLTextAreaElement;
      const start = target.selectionStart;
      const end = target.selectionEnd;
      const newCode = code.substring(0, start) + '    ' + code.substring(end);
      setCode(newCode);
      // Set cursor position after inserted spaces
      setTimeout(() => {
        target.selectionStart = target.selectionEnd = start + 4;
      }, 0);
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
      {/* Header */}
      <div className="mb-3">
        <span className={`text-xs uppercase tracking-wide ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>
          Fix {lineLabel}:
        </span>
        <div
          className={`mt-1 font-mono text-sm px-3 py-1.5 rounded ${
            isDark ? 'bg-red-900/20 text-red-300 border border-red-800/50' : 'bg-red-50 text-red-700 border border-red-200'
          }`}
        >
          {buggyLinesText.map((line, i) => (
            <div key={i}>{line}</div>
          ))}
        </div>
      </div>

      {/* Code editor */}
      <div className="mb-3">
        <span className={`text-xs uppercase tracking-wide ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>
          Write your fix:
        </span>
        <textarea
          value={code}
          onChange={(e) => setCode(e.target.value)}
          onKeyDown={handleKeyDown}
          rows={Math.max(2, buggyLinesText.length + 1)}
          spellCheck={false}
          className={`mt-1 w-full font-mono text-sm px-3 py-2 rounded border resize-y ${
            isDark
              ? 'bg-gray-900 text-gray-100 border-gray-600 focus:border-primary-500'
              : 'bg-white text-gray-900 border-gray-300 focus:border-primary-500'
          } focus:outline-none focus:ring-1 focus:ring-primary-500`}
        />
        <p className={`text-xs mt-1 ${isDark ? 'text-gray-600' : 'text-gray-400'}`}>
          Ctrl/Cmd+Enter to run tests
        </p>
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

      {/* Test results inline */}
      <AnimatePresence>
        {showTestResults && testResults.length > 0 && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="mb-3 space-y-1.5"
          >
            <span className={`text-xs uppercase tracking-wide ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>
              Test Results:
            </span>
            {testResults.map((result, i) => (
              <motion.div
                key={result.testId}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.1 }}
                className={`p-2 rounded text-xs font-mono ${
                  result.passed
                    ? isDark ? 'bg-green-900/20 text-green-300' : 'bg-green-50 text-green-700'
                    : isDark ? 'bg-red-900/20 text-red-300' : 'bg-red-50 text-red-700'
                }`}
              >
                <div className="flex items-center gap-2">
                  <span>{result.passed ? '\u2713' : '\u2717'}</span>
                  <span>Test {i + 1}</span>
                </div>
                {!result.passed && (
                  <div className="ml-5 mt-1 space-y-0.5">
                    <div>
                      <span className={isDark ? 'text-gray-500' : 'text-gray-400'}>Expected: </span>
                      <span>{result.expectedOutput}</span>
                    </div>
                    <div>
                      <span className={isDark ? 'text-gray-500' : 'text-gray-400'}>Got: </span>
                      <span className="text-red-400">{result.actualOutput}</span>
                    </div>
                    {result.error && (
                      <div className="text-red-400 italic">{result.error}</div>
                    )}
                  </div>
                )}
              </motion.div>
            ))}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Run tests button */}
      <motion.button
        whileHover={!executionPending ? { scale: 1.02 } : {}}
        whileTap={!executionPending ? { scale: 0.98 } : {}}
        onClick={handleRunTests}
        disabled={executionPending || code.trim().length === 0}
        className={`w-full py-2.5 rounded-lg font-medium text-sm transition-colors ${
          !executionPending && code.trim().length > 0
            ? 'bg-primary-500 text-white hover:bg-primary-600'
            : isDark
            ? 'bg-gray-700 text-gray-500 cursor-not-allowed'
            : 'bg-gray-200 text-gray-400 cursor-not-allowed'
        }`}
      >
        {executionPending ? (
          <span className="flex items-center justify-center gap-2">
            <motion.span
              animate={{ rotate: 360 }}
              transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
              className="inline-block w-4 h-4 border-2 border-current border-t-transparent rounded-full"
            />
            Running Tests...
          </span>
        ) : (
          'Run Tests'
        )}
      </motion.button>
    </motion.div>
  );
}
