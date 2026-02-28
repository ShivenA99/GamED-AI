'use client';

import { useState, useCallback, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { EnhancedLabel, EnhancedDistractorLabel, DistractorLabel } from './types';

interface DistractorManagerProps {
  /** Real labels available */
  realLabels: EnhancedLabel[];
  /** Distractor labels to mix in */
  distractorLabels: (DistractorLabel | EnhancedDistractorLabel)[];
  /** Rejection mode */
  rejectionMode?: 'immediate' | 'deferred';
  /** Shuffle labels together */
  shuffle?: boolean;
  /** Callback when distractor is rejected (immediate mode) */
  onDistractorRejected?: (distractorId: string, explanation: string) => void;
  /** Children render prop with mixed labels */
  children: (props: {
    mixedLabels: (EnhancedLabel | EnhancedDistractorLabel)[];
    isDistractor: (id: string) => boolean;
    handlePlacementAttempt: (labelId: string, zoneId: string) => 'real' | 'distractor_rejected' | 'distractor_deferred';
    rejectedDistractors: Array<{ id: string; text: string; explanation: string }>;
    dismissRejection: () => void;
  }) => React.ReactNode;
}

function shuffleArray<T>(arr: T[]): T[] {
  const shuffled = [...arr];
  for (let i = shuffled.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]];
  }
  return shuffled;
}

export default function DistractorManager({
  realLabels,
  distractorLabels,
  rejectionMode = 'immediate',
  shuffle = true,
  onDistractorRejected,
  children,
}: DistractorManagerProps) {
  const [removedDistractors, setRemovedDistractors] = useState<Set<string>>(new Set());
  const [rejectedDistractors, setRejectedDistractors] = useState<
    Array<{ id: string; text: string; explanation: string }>
  >([]);

  // Set of distractor IDs for quick lookup
  const distractorIds = useMemo(
    () => new Set(distractorLabels.map((d) => d.id)),
    [distractorLabels]
  );

  // Mix labels, filtering out removed distractors
  const mixedLabels = useMemo(() => {
    const activeDistractors = distractorLabels.filter(
      (d) => !removedDistractors.has(d.id)
    );
    const combined: (EnhancedLabel | EnhancedDistractorLabel)[] = [
      ...realLabels,
      ...activeDistractors,
    ];
    return shuffle ? shuffleArray(combined) : combined;
  }, [realLabels, distractorLabels, removedDistractors, shuffle]);

  const isDistractor = useCallback(
    (id: string) => distractorIds.has(id),
    [distractorIds]
  );

  const handlePlacementAttempt = useCallback(
    (labelId: string, _zoneId: string): 'real' | 'distractor_rejected' | 'distractor_deferred' => {
      if (!distractorIds.has(labelId)) {
        return 'real';
      }

      const distractor = distractorLabels.find((d) => d.id === labelId);
      if (!distractor) return 'real';

      if (rejectionMode === 'immediate') {
        // Remove from tray and show explanation
        setRemovedDistractors((prev) => new Set([...prev, labelId]));
        const explanation = distractor.explanation || 'This is not a correct answer.';
        setRejectedDistractors((prev) => [
          ...prev,
          { id: labelId, text: distractor.text, explanation },
        ]);
        onDistractorRejected?.(labelId, explanation);
        return 'distractor_rejected';
      }

      // Deferred: let it be placed, will be evaluated on submit
      return 'distractor_deferred';
    },
    [distractorIds, distractorLabels, rejectionMode, onDistractorRejected]
  );

  const dismissRejection = useCallback(() => {
    setRejectedDistractors([]);
  }, []);

  return (
    <>
      {children({
        mixedLabels,
        isDistractor,
        handlePlacementAttempt,
        rejectedDistractors,
        dismissRejection,
      })}

      {/* Rejection popup */}
      <AnimatePresence>
        {rejectedDistractors.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 20 }}
            className="fixed bottom-6 left-1/2 -translate-x-1/2 z-50 max-w-md"
          >
            <div className="bg-amber-50 dark:bg-amber-900/90 border border-amber-300 dark:border-amber-700 rounded-xl shadow-xl p-4">
              <div className="flex items-start gap-3">
                <span className="text-amber-500 text-xl flex-shrink-0">⚠️</span>
                <div className="flex-1">
                  <p className="font-medium text-amber-800 dark:text-amber-200 text-sm mb-1">
                    Not quite!
                  </p>
                  <p className="text-amber-700 dark:text-amber-300 text-sm">
                    <strong>{rejectedDistractors[rejectedDistractors.length - 1].text}</strong>
                    {' — '}
                    {rejectedDistractors[rejectedDistractors.length - 1].explanation}
                  </p>
                </div>
                <button
                  onClick={dismissRejection}
                  className="text-amber-500 hover:text-amber-700 dark:hover:text-amber-300 flex-shrink-0"
                  aria-label="Dismiss"
                >
                  ✕
                </button>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
