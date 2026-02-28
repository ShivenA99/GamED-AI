'use client';

import { useCallback } from 'react';
import { motion } from 'framer-motion';
import {
  BoardRendererProps,
  SequenceBuildingBoardConfig,
} from '../constraintPuzzleTypes';

export default function SequenceBuildingBoard({
  config,
  state,
  dispatch,
  disabled = false,
  theme = 'dark',
}: BoardRendererProps) {
  const isDark = theme === 'dark';
  const cfg = config as SequenceBuildingBoardConfig;
  const { items, showArrows = true } = cfg;

  const availableItems = items.filter((it) => !state.sequence.includes(it.id));

  const handleAdd = useCallback(
    (id: string) => {
      if (!disabled) dispatch({ type: 'ADD_TO_SEQUENCE', id });
    },
    [disabled, dispatch],
  );

  const handleRemove = useCallback(
    (id: string) => {
      if (!disabled) dispatch({ type: 'REMOVE_FROM_SEQUENCE', id });
    },
    [disabled, dispatch],
  );

  const handleMoveUp = useCallback(
    (index: number) => {
      if (disabled || index === 0) return;
      const newSeq = [...state.sequence];
      [newSeq[index - 1], newSeq[index]] = [newSeq[index], newSeq[index - 1]];
      dispatch({ type: 'SET_SEQUENCE', sequence: newSeq });
    },
    [disabled, state.sequence, dispatch],
  );

  const handleMoveDown = useCallback(
    (index: number) => {
      if (disabled || index >= state.sequence.length - 1) return;
      const newSeq = [...state.sequence];
      [newSeq[index], newSeq[index + 1]] = [newSeq[index + 1], newSeq[index]];
      dispatch({ type: 'SET_SEQUENCE', sequence: newSeq });
    },
    [disabled, state.sequence, dispatch],
  );

  const itemById = (id: string) => items.find((it) => it.id === id);

  return (
    <div className="space-y-4">
      <div className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
        Sequence: {state.sequence.length}/{items.length}
      </div>

      {/* Current sequence */}
      <div>
        <div className={`text-sm font-medium mb-2 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
          Your Sequence
        </div>
        {state.sequence.length === 0 ? (
          <div className={`text-sm italic p-4 rounded-lg border-2 border-dashed text-center ${
            isDark ? 'text-gray-500 border-gray-700' : 'text-gray-400 border-gray-200'
          }`}>
            Click items below to add them to the sequence
          </div>
        ) : (
          <div className="space-y-1">
            {state.sequence.map((id, index) => {
              const item = itemById(id);
              if (!item) return null;
              return (
                <motion.div
                  key={id}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  className={`flex items-center gap-2 p-2 rounded-lg border ${
                    isDark
                      ? 'border-blue-700 bg-blue-900/20'
                      : 'border-blue-300 bg-blue-50'
                  }`}
                >
                  {/* Position number */}
                  <span className={`text-xs font-bold w-6 text-center ${isDark ? 'text-blue-400' : 'text-blue-600'}`}>
                    {index + 1}
                  </span>

                  {/* Arrow between items */}
                  {showArrows && index > 0 && (
                    <span className={`text-xs ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>
                      {'\u2192'}
                    </span>
                  )}

                  {/* Item label */}
                  {item.icon && <span className="text-lg">{item.icon}</span>}
                  <span className={`text-sm font-medium flex-1 ${isDark ? 'text-gray-200' : 'text-gray-800'}`}>
                    {item.label}
                  </span>

                  {/* Move + remove buttons */}
                  {!disabled && (
                    <div className="flex items-center gap-1">
                      <button
                        onClick={() => handleMoveUp(index)}
                        disabled={index === 0}
                        className={`p-1 rounded text-xs ${
                          index === 0
                            ? isDark ? 'text-gray-600' : 'text-gray-300'
                            : isDark ? 'text-gray-400 hover:text-white' : 'text-gray-500 hover:text-gray-900'
                        }`}
                      >
                        {'\u25B2'}
                      </button>
                      <button
                        onClick={() => handleMoveDown(index)}
                        disabled={index >= state.sequence.length - 1}
                        className={`p-1 rounded text-xs ${
                          index >= state.sequence.length - 1
                            ? isDark ? 'text-gray-600' : 'text-gray-300'
                            : isDark ? 'text-gray-400 hover:text-white' : 'text-gray-500 hover:text-gray-900'
                        }`}
                      >
                        {'\u25BC'}
                      </button>
                      <button
                        onClick={() => handleRemove(id)}
                        className={`p-1 rounded text-xs ${
                          isDark ? 'text-red-400 hover:text-red-300' : 'text-red-500 hover:text-red-700'
                        }`}
                      >
                        {'\u2715'}
                      </button>
                    </div>
                  )}
                </motion.div>
              );
            })}
          </div>
        )}
      </div>

      {/* Available items */}
      {availableItems.length > 0 && (
        <div>
          <div className={`text-sm font-medium mb-2 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
            Available Items
          </div>
          <div className="flex flex-wrap gap-2">
            {availableItems.map((item) => (
              <motion.button
                key={item.id}
                whileHover={{ scale: disabled ? 1 : 1.03 }}
                whileTap={{ scale: disabled ? 1 : 0.97 }}
                onClick={() => handleAdd(item.id)}
                disabled={disabled}
                className={`px-3 py-2 rounded-lg border text-sm font-medium transition-all ${
                  isDark
                    ? 'border-gray-600 bg-gray-800 text-gray-300 hover:border-gray-400'
                    : 'border-gray-200 bg-white text-gray-700 hover:border-gray-400'
                } ${disabled ? 'cursor-default opacity-70' : 'cursor-pointer'}`}
              >
                {item.icon && <span className="mr-1">{item.icon}</span>}
                {item.label}
              </motion.button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
