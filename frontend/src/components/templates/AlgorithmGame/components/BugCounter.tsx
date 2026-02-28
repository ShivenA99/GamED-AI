'use client';

import { motion } from 'framer-motion';

interface BugCounterProps {
  total: number;
  found: number;
  theme?: 'dark' | 'light';
}

export default function BugCounter({ total, found, theme = 'dark' }: BugCounterProps) {
  const isDark = theme === 'dark';

  return (
    <div className="flex items-center gap-1.5">
      <span className={`text-xs font-medium ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
        Bugs:
      </span>
      <div className="flex gap-1">
        {Array.from({ length: total }).map((_, i) => (
          <motion.div
            key={i}
            initial={false}
            animate={
              i < found
                ? { scale: [1, 1.3, 1], backgroundColor: 'var(--bug-found)' }
                : {}
            }
            transition={{ duration: 0.3 }}
            className={`w-5 h-5 rounded-full flex items-center justify-center text-xs font-bold ${
              i < found
                ? 'bg-green-500 text-white'
                : isDark
                ? 'bg-gray-700 text-gray-500 border border-gray-600'
                : 'bg-gray-200 text-gray-400 border border-gray-300'
            }`}
          >
            {i < found ? '\u2713' : i + 1}
          </motion.div>
        ))}
      </div>
    </div>
  );
}
