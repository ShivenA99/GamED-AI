'use client';

import { useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

interface FeedbackToastProps {
  message: string | null;
  type: 'success' | 'error' | 'info' | null;
  onDismiss: () => void;
  autoDismissMs?: number;
  theme?: 'dark' | 'light';
}

export default function FeedbackToast({
  message,
  type,
  onDismiss,
  autoDismissMs = 3000,
  theme = 'dark',
}: FeedbackToastProps) {
  const isDark = theme === 'dark';

  useEffect(() => {
    if (message && type !== 'success') {
      const timer = setTimeout(onDismiss, autoDismissMs);
      return () => clearTimeout(timer);
    }
  }, [message, type, onDismiss, autoDismissMs]);

  const bgColor =
    type === 'success'
      ? isDark ? 'bg-green-900/90 border-green-700' : 'bg-green-50 border-green-200'
      : type === 'error'
      ? isDark ? 'bg-red-900/90 border-red-700' : 'bg-red-50 border-red-200'
      : isDark ? 'bg-blue-900/90 border-blue-700' : 'bg-blue-50 border-blue-200';

  const textColor =
    type === 'success'
      ? isDark ? 'text-green-200' : 'text-green-800'
      : type === 'error'
      ? isDark ? 'text-red-200' : 'text-red-800'
      : isDark ? 'text-blue-200' : 'text-blue-800';

  const icon =
    type === 'success' ? '\u2713' : type === 'error' ? '\u2717' : '\u2139';

  return (
    <AnimatePresence>
      {message && (
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -20 }}
          transition={{ type: 'spring', stiffness: 300, damping: 25 }}
          className={`p-3 rounded-lg border text-sm ${bgColor} ${textColor}`}
        >
          <div className="flex items-start gap-2">
            <span className="flex-shrink-0 font-bold">{icon}</span>
            <p className="flex-1">{message}</p>
            <button
              onClick={onDismiss}
              className="flex-shrink-0 opacity-60 hover:opacity-100 transition-opacity"
            >
              \u2715
            </button>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
