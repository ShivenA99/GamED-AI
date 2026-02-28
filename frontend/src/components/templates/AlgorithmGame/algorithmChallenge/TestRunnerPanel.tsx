'use client';

import { motion } from 'framer-motion';
import { TestRunResult } from './combinedPuzzleTypes';

interface TestRunnerPanelProps {
  results: TestRunResult[];
  passRate: number;
  theme?: 'dark' | 'light';
}

export default function TestRunnerPanel({
  results,
  passRate,
  theme = 'dark',
}: TestRunnerPanelProps) {
  const isDark = theme === 'dark';

  if (results.length === 0) return null;

  const passCount = results.filter((r) => r.passed).length;

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className={`rounded-xl border ${isDark ? 'border-gray-700 bg-gray-900' : 'border-gray-200 bg-white'}`}
    >
      {/* Header with pass rate bar */}
      <div className={`px-4 py-3 border-b ${isDark ? 'border-gray-700' : 'border-gray-200'}`}>
        <div className="flex items-center justify-between mb-2">
          <span className={`text-sm font-semibold ${isDark ? 'text-gray-200' : 'text-gray-800'}`}>
            Test Results
          </span>
          <span className={`text-xs font-medium ${
            passRate >= 1 ? 'text-green-400' : passRate >= 0.5 ? 'text-yellow-400' : 'text-red-400'
          }`}>
            {passCount}/{results.length} passed
          </span>
        </div>

        {/* Progress bar */}
        <div className={`h-1.5 rounded-full overflow-hidden ${isDark ? 'bg-gray-800' : 'bg-gray-200'}`}>
          <motion.div
            initial={{ width: 0 }}
            animate={{ width: `${passRate * 100}%` }}
            transition={{ duration: 0.5, ease: 'easeOut' }}
            className={`h-full rounded-full ${
              passRate >= 1 ? 'bg-green-500' : passRate >= 0.5 ? 'bg-yellow-500' : 'bg-red-500'
            }`}
          />
        </div>
      </div>

      {/* Results table */}
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className={isDark ? 'text-gray-400' : 'text-gray-500'}>
              <th className="text-left px-4 py-2 font-medium">Test</th>
              <th className="text-left px-4 py-2 font-medium">Expected</th>
              <th className="text-left px-4 py-2 font-medium">Got</th>
              <th className="text-center px-4 py-2 font-medium">Status</th>
              <th className="text-right px-4 py-2 font-medium">Time</th>
            </tr>
          </thead>
          <tbody>
            {results.map((r, i) => (
              <motion.tr
                key={r.testId}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.05 }}
                className={`border-t ${isDark ? 'border-gray-800' : 'border-gray-100'}`}
              >
                <td className={`px-4 py-2 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
                  <div className="flex items-center gap-1.5">
                    {r.isPuzzleCase && (
                      <span className="text-[10px] px-1 py-0.5 rounded bg-blue-600/20 text-blue-400 font-medium">
                        PUZZLE
                      </span>
                    )}
                    {r.label}
                  </div>
                </td>
                <td className="px-4 py-2">
                  <code className={`text-xs ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
                    {truncate(r.expectedOutput, 40)}
                  </code>
                </td>
                <td className="px-4 py-2">
                  <code className={`text-xs ${
                    r.error
                      ? 'text-red-400'
                      : r.passed
                        ? isDark ? 'text-green-400' : 'text-green-600'
                        : isDark ? 'text-yellow-400' : 'text-yellow-600'
                  }`}>
                    {truncate(r.actualOutput, 40)}
                  </code>
                </td>
                <td className="px-4 py-2 text-center">
                  {r.error ? (
                    <span className="text-red-400 text-xs font-medium">ERROR</span>
                  ) : r.passed ? (
                    <span className="text-green-400 text-xs font-medium">PASS</span>
                  ) : (
                    <span className="text-yellow-400 text-xs font-medium">FAIL</span>
                  )}
                </td>
                <td className={`px-4 py-2 text-right text-xs ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>
                  {r.executionTimeMs.toFixed(0)}ms
                </td>
              </motion.tr>
            ))}
          </tbody>
        </table>
      </div>
    </motion.div>
  );
}

function truncate(s: string, max: number): string {
  return s.length > max ? s.slice(0, max) + '...' : s;
}
