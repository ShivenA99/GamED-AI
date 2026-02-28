'use client';

import { motion } from 'framer-motion';
import { TestCase } from '../types';

interface TestCasePanelProps {
  testCases: TestCase[];
  fixedBugIds: string[];
  showVerification?: boolean;
  theme?: 'dark' | 'light';
}

export default function TestCasePanel({
  testCases,
  fixedBugIds,
  showVerification = false,
  theme = 'dark',
}: TestCasePanelProps) {
  const isDark = theme === 'dark';

  const getTestStatus = (tc: TestCase): 'pass' | 'fail' | 'fixed' => {
    // If all bugs this test exposes are fixed, it now passes
    const allExposedFixed = tc.exposedBugs.every((bid) => fixedBugIds.includes(bid));
    if (allExposedFixed && tc.exposedBugs.length > 0) return 'fixed';
    // If expected === buggy, it was always passing
    if (tc.expectedOutput === tc.buggyOutput) return 'pass';
    return 'fail';
  };

  return (
    <div className="space-y-3">
      <h3
        className={`text-sm font-semibold uppercase tracking-wide ${
          isDark ? 'text-gray-400' : 'text-gray-500'
        }`}
      >
        Test Cases
      </h3>

      {testCases.map((tc, i) => {
        const status = getTestStatus(tc);
        const isPass = status === 'pass' || status === 'fixed';

        return (
          <motion.div
            key={tc.id}
            initial={showVerification ? { opacity: 0, x: 10 } : false}
            animate={showVerification ? { opacity: 1, x: 0 } : undefined}
            transition={showVerification ? { delay: i * 0.2 } : undefined}
            className={`p-3 rounded-lg border text-sm ${
              isDark
                ? `border-gray-700 ${isPass ? 'bg-green-900/10' : 'bg-red-900/10'}`
                : `border-gray-200 ${isPass ? 'bg-green-50' : 'bg-red-50'}`
            }`}
          >
            {/* Status icon + test name */}
            <div className="flex items-center gap-2 mb-2">
              <span className={`text-base ${isPass ? 'text-green-400' : 'text-red-400'}`}>
                {isPass ? '\u2713' : '\u2717'}
              </span>
              <span
                className={`font-medium ${isDark ? 'text-gray-200' : 'text-gray-800'}`}
              >
                Test {i + 1}
                {status === 'fixed' && (
                  <span className="ml-2 text-xs text-green-400 font-normal">FIXED</span>
                )}
              </span>
            </div>

            {/* Input */}
            <div className={`font-mono text-xs mb-1 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
              {tc.inputDescription}
            </div>

            {/* Expected vs Got */}
            <div className="flex gap-4 mt-2">
              <div>
                <span className={`text-xs ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>
                  Expected:{' '}
                </span>
                <span
                  className={`font-mono font-medium ${
                    isDark ? 'text-gray-200' : 'text-gray-800'
                  }`}
                >
                  {tc.expectedOutput}
                </span>
              </div>
              {!isPass && (
                <div>
                  <span className={`text-xs ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>
                    Got:{' '}
                  </span>
                  <span className="font-mono font-medium text-red-400">
                    {tc.buggyOutput}
                  </span>
                </div>
              )}
            </div>
          </motion.div>
        );
      })}
    </div>
  );
}
