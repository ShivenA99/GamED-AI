'use client';

import { motion } from 'framer-motion';
import { CoinChangePuzzleData } from '../types';

interface CoinChangeBoardProps {
  data: CoinChangePuzzleData;
  selectedCoins: number[];
  onAddCoin: (denomination: number) => void;
  onRemoveCoin: (index: number) => void;
  disabled?: boolean;
  theme?: 'dark' | 'light';
}

export default function CoinChangeBoard({
  data,
  selectedCoins,
  onAddCoin,
  onRemoveCoin,
  disabled = false,
  theme = 'dark',
}: CoinChangeBoardProps) {
  const isDark = theme === 'dark';
  const currentSum = selectedCoins.reduce((s, c) => s + c, 0);
  const remaining = data.targetAmount - currentSum;
  const pct = Math.min((currentSum / data.targetAmount) * 100, 100);

  return (
    <div className="space-y-4">
      {/* Target progress */}
      <div className={`rounded-lg p-3 ${isDark ? 'bg-gray-800' : 'bg-gray-50'}`}>
        <div className="flex justify-between text-sm mb-2">
          <span className={isDark ? 'text-gray-400' : 'text-gray-500'}>
            Total: {currentSum}/{data.targetAmount}
          </span>
          <span className={remaining === 0 ? (isDark ? 'text-green-400' : 'text-green-600') : (isDark ? 'text-blue-400' : 'text-blue-600')}>
            {remaining === 0 ? 'Exact match!' : `Remaining: ${remaining}`}
          </span>
        </div>
        <div className={`h-3 rounded-full overflow-hidden ${isDark ? 'bg-gray-700' : 'bg-gray-200'}`}>
          <motion.div
            className={`h-full rounded-full ${
              currentSum > data.targetAmount ? 'bg-red-500' : currentSum === data.targetAmount ? 'bg-green-500' : 'bg-blue-500'
            }`}
            animate={{ width: `${pct}%` }}
            transition={{ type: 'spring', stiffness: 300, damping: 25 }}
          />
        </div>
      </div>

      {/* Available denominations */}
      <div>
        <div className={`text-sm font-medium mb-2 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
          Available Coins
        </div>
        <div className="flex flex-wrap gap-3">
          {data.denominations
            .sort((a, b) => b - a)
            .map((d) => (
              <motion.button
                key={d}
                whileHover={{ scale: disabled ? 1 : 1.05 }}
                whileTap={{ scale: disabled ? 1 : 0.95 }}
                onClick={() => !disabled && onAddCoin(d)}
                disabled={disabled}
                className={`w-14 h-14 rounded-full border-2 flex items-center justify-center font-bold transition-all ${
                  isDark
                    ? 'border-yellow-600 bg-yellow-900/30 text-yellow-300 hover:bg-yellow-800/40'
                    : 'border-yellow-500 bg-yellow-50 text-yellow-700 hover:bg-yellow-100'
                } ${disabled ? 'cursor-default opacity-70' : 'cursor-pointer'}`}
              >
                {d}
              </motion.button>
            ))}
        </div>
      </div>

      {/* Selected coins */}
      <div>
        <div className={`text-sm font-medium mb-2 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
          Your Selection ({selectedCoins.length} coins)
        </div>
        {selectedCoins.length === 0 ? (
          <div className={`text-sm italic ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>
            Click coins above to add them
          </div>
        ) : (
          <div className="flex flex-wrap gap-2">
            {selectedCoins.map((coin, i) => (
              <motion.button
                key={i}
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                exit={{ scale: 0 }}
                whileHover={{ scale: disabled ? 1 : 1.1 }}
                onClick={() => !disabled && onRemoveCoin(i)}
                disabled={disabled}
                className={`w-11 h-11 rounded-full border-2 flex items-center justify-center text-sm font-bold transition-all ${
                  isDark
                    ? 'border-blue-600 bg-blue-900/30 text-blue-300 hover:border-red-500 hover:bg-red-900/30'
                    : 'border-blue-500 bg-blue-50 text-blue-700 hover:border-red-500 hover:bg-red-50'
                } ${disabled ? 'cursor-default' : 'cursor-pointer'}`}
                title="Click to remove"
              >
                {coin}
              </motion.button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
