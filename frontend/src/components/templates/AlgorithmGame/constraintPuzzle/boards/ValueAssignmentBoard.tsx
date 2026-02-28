'use client';

import { useState } from 'react';
import { motion } from 'framer-motion';
import {
  BoardRendererProps,
  ValueAssignmentBoardConfig,
} from '../constraintPuzzleTypes';

export default function ValueAssignmentBoard({
  config,
  state,
  dispatch,
  disabled = false,
  theme = 'dark',
}: BoardRendererProps) {
  const isDark = theme === 'dark';
  const cfg = config as ValueAssignmentBoardConfig;
  const { slots, domain, domainColors = {} } = cfg;
  const layout = cfg.layout ?? 'list';

  const [activeSlot, setActiveSlot] = useState<string | null>(null);

  const assignedCount = Object.values(state.assignments).filter((v) => v != null).length;

  const handleSlotClick = (slotId: string) => {
    if (disabled) return;
    if (activeSlot === slotId) {
      setActiveSlot(null);
    } else {
      setActiveSlot(slotId);
    }
  };

  const handleValueSelect = (slotId: string, value: string | number) => {
    if (disabled) return;
    const current = state.assignments[slotId];
    if (current === value) {
      dispatch({ type: 'CLEAR_ASSIGNMENT', slotId });
    } else {
      dispatch({ type: 'ASSIGN', slotId, value });
    }
    setActiveSlot(null);
  };

  // Check if a slot has a neighbor conflict
  const hasNeighborConflict = (slotId: string): boolean => {
    const val = state.assignments[slotId];
    if (val == null) return false;
    const slot = slots.find((s) => s.id === slotId);
    if (!slot?.neighbors) return false;
    return slot.neighbors.some((nId) => state.assignments[nId] === val);
  };

  const getValueColor = (value: string | number): string => {
    const colorStr = domainColors[String(value)];
    return colorStr ?? (isDark ? '#6b7280' : '#9ca3af');
  };

  return (
    <div className="space-y-4">
      <div className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
        Assigned: {assignedCount}/{slots.length}
      </div>

      {/* Domain legend */}
      <div className="flex flex-wrap gap-2">
        {domain.map((val) => (
          <div key={String(val)} className="flex items-center gap-1.5">
            <div
              className="w-4 h-4 rounded-full border"
              style={{
                backgroundColor: getValueColor(val),
                borderColor: isDark ? '#4b5563' : '#d1d5db',
              }}
            />
            <span className={`text-xs ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
              {String(val)}
            </span>
          </div>
        ))}
      </div>

      {/* Slots */}
      <div className={
        layout === 'grid'
          ? 'grid grid-cols-3 sm:grid-cols-4 gap-3'
          : 'space-y-2'
      }>
        {slots.map((slot) => {
          const assigned = state.assignments[slot.id];
          const conflict = hasNeighborConflict(slot.id);
          const isActive = activeSlot === slot.id;

          return (
            <div key={slot.id} className="relative">
              <motion.button
                whileHover={{ scale: disabled ? 1 : 1.02 }}
                onClick={() => handleSlotClick(slot.id)}
                disabled={disabled}
                className={`w-full p-3 rounded-lg border-2 text-left transition-all ${
                  conflict
                    ? isDark
                      ? 'border-red-500 bg-red-900/20'
                      : 'border-red-500 bg-red-50'
                    : assigned != null
                      ? isDark
                        ? 'border-blue-500 bg-gray-800'
                        : 'border-blue-500 bg-blue-50'
                      : isActive
                        ? isDark
                          ? 'border-blue-400 bg-gray-800'
                          : 'border-blue-400 bg-white'
                        : isDark
                          ? 'border-gray-600 bg-gray-800 hover:border-gray-500'
                          : 'border-gray-200 bg-white hover:border-gray-400'
                } ${disabled ? 'cursor-default' : 'cursor-pointer'}`}
              >
                <div className="flex items-center justify-between">
                  <span className={`text-sm font-medium ${isDark ? 'text-gray-200' : 'text-gray-800'}`}>
                    {slot.label}
                  </span>
                  {assigned != null && (
                    <div
                      className="w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold text-white"
                      style={{ backgroundColor: getValueColor(assigned) }}
                    >
                      {String(assigned).charAt(0).toUpperCase()}
                    </div>
                  )}
                </div>
                {slot.neighbors && slot.neighbors.length > 0 && (
                  <div className={`text-xs mt-1 ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>
                    Neighbors: {slot.neighbors.join(', ')}
                  </div>
                )}
              </motion.button>

              {/* Value picker dropdown */}
              {isActive && !disabled && (
                <motion.div
                  initial={{ opacity: 0, y: -5 }}
                  animate={{ opacity: 1, y: 0 }}
                  className={`absolute z-10 mt-1 left-0 right-0 p-2 rounded-lg border shadow-lg ${
                    isDark ? 'bg-gray-800 border-gray-600' : 'bg-white border-gray-200'
                  }`}
                >
                  <div className="flex flex-wrap gap-2">
                    {domain.map((val) => {
                      const isAssigned = assigned === val;
                      return (
                        <button
                          key={String(val)}
                          onClick={(e) => {
                            e.stopPropagation();
                            handleValueSelect(slot.id, val);
                          }}
                          className={`px-3 py-1.5 rounded-md text-sm font-medium transition-all border ${
                            isAssigned
                              ? 'text-white border-transparent'
                              : isDark
                                ? 'text-gray-200 border-gray-600 hover:border-gray-400'
                                : 'text-gray-800 border-gray-200 hover:border-gray-400'
                          }`}
                          style={isAssigned ? { backgroundColor: getValueColor(val) } : undefined}
                        >
                          {String(val)}
                        </button>
                      );
                    })}
                    {assigned != null && (
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          dispatch({ type: 'CLEAR_ASSIGNMENT', slotId: slot.id });
                          setActiveSlot(null);
                        }}
                        className={`px-3 py-1.5 rounded-md text-sm font-medium border ${
                          isDark
                            ? 'text-red-400 border-red-800 hover:bg-red-900/30'
                            : 'text-red-600 border-red-200 hover:bg-red-50'
                        }`}
                      >
                        Clear
                      </button>
                    )}
                  </div>
                </motion.div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
