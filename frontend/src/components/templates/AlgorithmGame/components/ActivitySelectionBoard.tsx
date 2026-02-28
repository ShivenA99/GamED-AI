'use client';

import { motion } from 'framer-motion';
import { ActivitySelectionPuzzleData } from '../types';

interface ActivitySelectionBoardProps {
  data: ActivitySelectionPuzzleData;
  selectedActivityIds: string[];
  onToggleActivity: (activityId: string) => void;
  disabled?: boolean;
  theme?: 'dark' | 'light';
}

export default function ActivitySelectionBoard({
  data,
  selectedActivityIds,
  onToggleActivity,
  disabled = false,
  theme = 'dark',
}: ActivitySelectionBoardProps) {
  const isDark = theme === 'dark';

  const maxEnd = Math.max(...data.activities.map((a) => a.end));
  const timeSlots = maxEnd;
  const scale = (t: number) => (t / timeSlots) * 100;

  // Sort by start time
  const sorted = [...data.activities].sort((a, b) => a.start - b.start);

  return (
    <div className="space-y-4">
      <div className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
        Selected: {selectedActivityIds.length} activities
      </div>

      {/* Timeline visualization */}
      <div className={`rounded-lg p-4 ${isDark ? 'bg-gray-800' : 'bg-gray-50'}`}>
        {/* Time axis labels */}
        <div className="relative h-6 mb-2">
          {Array.from({ length: Math.ceil(timeSlots / 2) + 1 }).map((_, i) => {
            const t = i * 2;
            if (t > timeSlots) return null;
            return (
              <span
                key={t}
                className={`absolute text-[10px] ${isDark ? 'text-gray-500' : 'text-gray-400'}`}
                style={{ left: `${scale(t)}%`, transform: 'translateX(-50%)' }}
              >
                {t}
              </span>
            );
          })}
        </div>

        {/* Activities */}
        <div className="space-y-2">
          {sorted.map((activity) => {
            const isSelected = selectedActivityIds.includes(activity.id);
            const left = scale(activity.start);
            const width = scale(activity.end - activity.start);

            return (
              <motion.button
                key={activity.id}
                whileHover={{ scale: disabled ? 1 : 1.01 }}
                onClick={() => !disabled && onToggleActivity(activity.id)}
                disabled={disabled}
                className={`relative w-full h-10 ${disabled ? 'cursor-default' : 'cursor-pointer'}`}
              >
                {/* Background track */}
                <div className={`absolute inset-0 rounded ${isDark ? 'bg-gray-700/50' : 'bg-gray-200/50'}`} />

                {/* Activity bar */}
                <motion.div
                  className={`absolute top-0 h-full rounded flex items-center px-2 text-xs font-medium transition-colors ${
                    isSelected
                      ? isDark
                        ? 'bg-blue-700 text-blue-100 border border-blue-500'
                        : 'bg-blue-500 text-white border border-blue-600'
                      : isDark
                        ? 'bg-gray-600 text-gray-300 border border-gray-500 hover:bg-gray-500'
                        : 'bg-gray-300 text-gray-700 border border-gray-400 hover:bg-gray-400'
                  }`}
                  style={{ left: `${left}%`, width: `${width}%` }}
                  layout
                >
                  <span className="truncate">
                    {activity.name} ({activity.start}-{activity.end})
                  </span>
                </motion.div>
              </motion.button>
            );
          })}
        </div>
      </div>

      {/* Activity list */}
      <div className="grid grid-cols-2 gap-2">
        {sorted.map((activity) => {
          const isSelected = selectedActivityIds.includes(activity.id);
          return (
            <button
              key={activity.id}
              onClick={() => !disabled && onToggleActivity(activity.id)}
              disabled={disabled}
              className={`text-left p-2 rounded-lg border text-sm transition-all ${
                isSelected
                  ? isDark
                    ? 'border-blue-500 bg-blue-900/30 text-blue-200'
                    : 'border-blue-500 bg-blue-50 text-blue-700'
                  : isDark
                    ? 'border-gray-600 bg-gray-800 text-gray-300 hover:border-gray-500'
                    : 'border-gray-200 bg-white text-gray-700 hover:border-gray-400'
              } ${disabled ? 'cursor-default' : 'cursor-pointer'}`}
            >
              <div className="font-medium">{activity.name}</div>
              <div className={`text-xs ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
                {activity.start}:00 - {activity.end}:00
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
