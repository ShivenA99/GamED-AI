'use client';

import { motion } from 'framer-motion';

interface RoundHeaderProps {
  currentRound: number;  // 0-indexed
  totalRounds: number;
  roundTitle: string;
  theme?: 'dark' | 'light';
}

export default function RoundHeader({
  currentRound,
  totalRounds,
  roundTitle,
  theme = 'dark',
}: RoundHeaderProps) {
  const isDark = theme === 'dark';

  if (totalRounds <= 1) return null;

  return (
    <motion.div
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      className={`flex items-center gap-3 px-4 py-2 rounded-lg mb-3 ${
        isDark ? 'bg-gray-800/50' : 'bg-gray-100'
      }`}
    >
      <span className={`text-sm font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
        Round {currentRound + 1} of {totalRounds}
      </span>
      <span className={`text-xs ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>
        {roundTitle}
      </span>

      {/* Progress dots */}
      <div className="flex items-center gap-1.5 ml-auto">
        {Array.from({ length: totalRounds }, (_, i) => (
          <motion.div
            key={i}
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ delay: i * 0.05 }}
            className={`w-2 h-2 rounded-full ${
              i < currentRound
                ? 'bg-green-400'
                : i === currentRound
                ? 'bg-primary-500'
                : isDark
                ? 'bg-gray-600'
                : 'bg-gray-300'
            }`}
          />
        ))}
      </div>
    </motion.div>
  );
}
