'use client';

import { motion } from 'framer-motion';
import { KnapsackPuzzleData } from '../types';

interface KnapsackBoardProps {
  data: KnapsackPuzzleData;
  selectedItemIds: string[];
  onToggleItem: (itemId: string) => void;
  disabled?: boolean;
  theme?: 'dark' | 'light';
}

export default function KnapsackBoard({
  data,
  selectedItemIds,
  onToggleItem,
  disabled = false,
  theme = 'dark',
}: KnapsackBoardProps) {
  const isDark = theme === 'dark';

  const currentWeight = data.items
    .filter((it) => selectedItemIds.includes(it.id))
    .reduce((s, it) => s + it.weight, 0);
  const currentValue = data.items
    .filter((it) => selectedItemIds.includes(it.id))
    .reduce((s, it) => s + it.value, 0);

  const capacityPct = Math.min((currentWeight / data.capacity) * 100, 100);
  const isOverCapacity = currentWeight > data.capacity;

  return (
    <div className="space-y-4">
      {/* Capacity bar */}
      <div className={`rounded-lg p-3 ${isDark ? 'bg-gray-800' : 'bg-gray-50'}`}>
        <div className="flex justify-between text-sm mb-2">
          <span className={isDark ? 'text-gray-400' : 'text-gray-500'}>
            Weight: {currentWeight}/{data.capacity}
          </span>
          <span className={isDark ? 'text-blue-400' : 'text-blue-600'}>
            Value: {currentValue}
          </span>
        </div>
        <div className={`h-3 rounded-full overflow-hidden ${isDark ? 'bg-gray-700' : 'bg-gray-200'}`}>
          <motion.div
            className={`h-full rounded-full ${isOverCapacity ? 'bg-red-500' : capacityPct > 80 ? 'bg-yellow-500' : 'bg-green-500'}`}
            animate={{ width: `${capacityPct}%` }}
            transition={{ type: 'spring', stiffness: 300, damping: 25 }}
          />
        </div>
      </div>

      {/* Items grid */}
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
        {data.items.map((item) => {
          const isSelected = selectedItemIds.includes(item.id);
          return (
            <motion.button
              key={item.id}
              whileHover={{ scale: disabled ? 1 : 1.02 }}
              whileTap={{ scale: disabled ? 1 : 0.98 }}
              onClick={() => !disabled && onToggleItem(item.id)}
              disabled={disabled}
              className={`p-3 rounded-lg border-2 text-left transition-all ${
                isSelected
                  ? isDark
                    ? 'border-blue-500 bg-blue-900/30'
                    : 'border-blue-500 bg-blue-50'
                  : isDark
                    ? 'border-gray-600 bg-gray-800 hover:border-gray-500'
                    : 'border-gray-200 bg-white hover:border-gray-400'
              } ${disabled ? 'cursor-default opacity-70' : 'cursor-pointer'}`}
            >
              <div className="text-2xl mb-1">{item.icon}</div>
              <div className={`text-sm font-medium ${isDark ? 'text-gray-200' : 'text-gray-800'}`}>
                {item.name}
              </div>
              <div className={`text-xs mt-1 flex gap-3 ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
                <span>W: {item.weight}</span>
                <span>V: {item.value}</span>
              </div>
              {isSelected && (
                <div className={`text-xs mt-1 font-medium ${isDark ? 'text-blue-400' : 'text-blue-600'}`}>
                  Selected
                </div>
              )}
            </motion.button>
          );
        })}
      </div>
    </div>
  );
}
