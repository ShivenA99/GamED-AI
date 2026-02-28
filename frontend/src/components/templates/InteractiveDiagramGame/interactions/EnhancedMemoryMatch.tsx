'use client';

import React, { useState, useCallback, useMemo, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import type { MemoryMatchConfig, MemoryMatchPair, MechanicAction, ActionResult } from '../types';

export interface EnhancedMemoryMatchProps {
  config: MemoryMatchConfig;
  storeProgress?: { matchedPairIds: string[]; attempts: number; totalPairs: number } | null;
  /** V4 unified action dispatch */
  onAction?: (action: MechanicAction) => ActionResult | null;
}

type CardState = 'face_down' | 'face_up' | 'matched';

interface CardData {
  instanceId: string; // Unique per card instance (each pair has 2 cards)
  pairId: string;
  content: string;
  type: 'text' | 'image';
  side: 'front' | 'back';
  explanation?: string;
}

// ─── 3D Flip Card ───────────────────────────────────────────────────
function FlipCard({
  card,
  state,
  onClick,
  flipDuration,
  cardBackStyle,
  matchedBehavior,
}: {
  card: CardData;
  state: CardState;
  onClick: (instanceId: string) => void;
  flipDuration: number;
  cardBackStyle: string;
  matchedBehavior: string;
}) {
  const isFlipped = state === 'face_up' || state === 'matched';
  const isMatched = state === 'matched';

  const cardBackClasses = useMemo(() => {
    switch (cardBackStyle) {
      case 'gradient':
        return 'bg-gradient-to-br from-indigo-500 to-purple-600';
      case 'pattern':
        return 'bg-indigo-500 bg-[radial-gradient(circle,_rgba(255,255,255,0.15)_1px,_transparent_1px)] bg-[length:8px_8px]';
      case 'question_mark':
        return 'bg-indigo-600';
      default:
        return 'bg-gradient-to-br from-indigo-500 to-purple-600';
    }
  }, [cardBackStyle]);

  const matchedClasses = useMemo(() => {
    switch (matchedBehavior) {
      case 'fade':
        return 'opacity-40';
      case 'shrink':
        return 'scale-90 opacity-60';
      case 'checkmark':
        return 'ring-2 ring-green-400';
      default:
        return 'ring-2 ring-green-400';
    }
  }, [matchedBehavior]);

  return (
    <div
      className={`relative cursor-pointer perspective-500 ${isMatched ? matchedClasses : ''}`}
      style={{ perspective: '600px' }}
      onClick={() => !isMatched && onClick(card.instanceId)}
    >
      <motion.div
        className="relative w-full aspect-[3/4] preserve-3d"
        animate={{ rotateY: isFlipped ? 180 : 0 }}
        transition={{ duration: flipDuration / 1000, ease: 'easeInOut' }}
        style={{ transformStyle: 'preserve-3d' }}
      >
        {/* Card Back */}
        <div
          className={`absolute inset-0 rounded-xl ${cardBackClasses} flex items-center justify-center shadow-lg border-2 border-indigo-400/30`}
          style={{ backfaceVisibility: 'hidden' }}
        >
          {cardBackStyle === 'question_mark' ? (
            <span className="text-4xl text-white/80 font-bold">?</span>
          ) : (
            <div className="w-10 h-10 rounded-full bg-white/20 flex items-center justify-center">
              <svg className="w-6 h-6 text-white/60" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
              </svg>
            </div>
          )}
        </div>

        {/* Card Face */}
        <div
          className={`absolute inset-0 rounded-xl bg-white dark:bg-gray-700 shadow-lg border-2 flex items-center justify-center p-3
            ${isMatched ? 'border-green-400' : 'border-gray-200 dark:border-gray-600'}
          `}
          style={{ backfaceVisibility: 'hidden', transform: 'rotateY(180deg)' }}
        >
          {card.type === 'image' ? (
            <img src={card.content} alt="" className="w-full h-full object-contain rounded" />
          ) : (
            <p className="text-sm font-medium text-gray-800 dark:text-gray-100 text-center leading-snug">
              {card.content}
            </p>
          )}

          {/* Matched checkmark */}
          {isMatched && (
            <div className="absolute top-1 right-1 w-6 h-6 bg-green-500 rounded-full flex items-center justify-center">
              <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
              </svg>
            </div>
          )}
        </div>
      </motion.div>
    </div>
  );
}

// ─── Match Particles ────────────────────────────────────────────────
function MatchParticles({ show }: { show: boolean }) {
  if (!show) return null;

  return (
    <div className="absolute inset-0 pointer-events-none z-50 overflow-hidden">
      {Array.from({ length: 12 }).map((_, i) => {
        const angle = (i / 12) * Math.PI * 2;
        const dist = 40 + Math.random() * 30;
        return (
          <motion.div
            key={i}
            className="absolute w-2 h-2 rounded-full bg-yellow-400"
            style={{ left: '50%', top: '50%' }}
            initial={{ scale: 1, opacity: 1, x: 0, y: 0 }}
            animate={{
              scale: 0,
              opacity: 0,
              x: Math.cos(angle) * dist,
              y: Math.sin(angle) * dist,
            }}
            transition={{ duration: 0.7, ease: 'easeOut' }}
          />
        );
      })}
    </div>
  );
}

// ─── Explanation Overlay ────────────────────────────────────────────
function ExplanationOverlay({
  explanation,
  show,
  onDismiss,
  durationMs = 3000,
}: {
  explanation: string;
  show: boolean;
  onDismiss: () => void;
  durationMs?: number;
}) {
  useEffect(() => {
    if (show) {
      const timer = setTimeout(onDismiss, durationMs);
      return () => clearTimeout(timer);
    }
  }, [show, onDismiss, durationMs]);

  return (
    <AnimatePresence>
      {show && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -10 }}
          className="fixed bottom-8 left-1/2 -translate-x-1/2 z-50 max-w-md"
        >
          <div className="bg-green-50 dark:bg-green-900/90 border border-green-300 dark:border-green-700 rounded-xl shadow-xl p-4">
            <div className="flex items-start gap-3">
              <span className="text-green-500 text-xl flex-shrink-0">✨</span>
              <div>
                <p className="font-medium text-green-800 dark:text-green-200 text-sm mb-0.5">Match found!</p>
                <p className="text-green-700 dark:text-green-300 text-sm">{explanation}</p>
              </div>
            </div>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

// ─── Stats Bar ──────────────────────────────────────────────────────
function StatsBar({
  matched,
  total,
  attempts,
}: {
  matched: number;
  total: number;
  attempts: number;
}) {
  const progressPct = total > 0 ? (matched / total) * 100 : 0;

  return (
    <div className="flex items-center justify-between px-4 py-3 bg-gray-50 dark:bg-gray-800/50 rounded-xl border border-gray-200 dark:border-gray-700 mb-4">
      <div className="flex items-center gap-4">
        <div className="text-sm">
          <span className="font-bold text-indigo-600 dark:text-indigo-400">{matched}</span>
          <span className="text-gray-500 dark:text-gray-400">/{total} matched</span>
        </div>
        <div className="text-sm">
          <span className="font-bold text-gray-700 dark:text-gray-200">{attempts}</span>
          <span className="text-gray-500 dark:text-gray-400"> attempts</span>
        </div>
      </div>

      {/* Progress bar */}
      <div className="w-32 h-2 bg-gray-200 dark:bg-gray-600 rounded-full overflow-hidden">
        <motion.div
          className="h-full bg-indigo-500 rounded-full"
          initial={{ width: 0 }}
          animate={{ width: `${progressPct}%` }}
          transition={{ type: 'spring', stiffness: 100 }}
        />
      </div>
    </div>
  );
}

// ─── Column Match Mode ──────────────────────────────────────────────
// Two visible columns: images on left, descriptions on right.
// User clicks left → right to connect. Submit to check all at once.
function ColumnMatchMode({
  pairs,
  instructions,
  show_explanation_on_match,
  onAction,
}: {
  pairs: MemoryMatchPair[];
  instructions: string;
  show_explanation_on_match: boolean;
  onAction?: (action: MechanicAction) => ActionResult | null;
}) {
  // Shuffle left (fronts) and right (backs) independently
  const shuffledLeft = useMemo(() => {
    const items = pairs.map(p => ({ pairId: p.id, content: p.front, type: p.frontType }));
    for (let i = items.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [items[i], items[j]] = [items[j], items[i]];
    }
    return items;
  }, [pairs]);

  const shuffledRight = useMemo(() => {
    const items = pairs.map(p => ({ pairId: p.id, content: p.back, type: p.backType }));
    for (let i = items.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [items[i], items[j]] = [items[j], items[i]];
    }
    return items;
  }, [pairs]);

  const [connections, setConnections] = useState<Map<string, string>>(new Map());
  const [selectedLeft, setSelectedLeft] = useState<string | null>(null);
  const [isSubmitted, setIsSubmitted] = useState(false);
  const [results, setResults] = useState<Map<string, boolean>>(new Map());
  const [showExplanation, setShowExplanation] = useState<string | null>(null);

  const leftRefs = useRef<Map<string, HTMLDivElement>>(new Map());
  const rightRefs = useRef<Map<string, HTMLDivElement>>(new Map());
  const containerRef = useRef<HTMLDivElement>(null);

  const allConnected = connections.size === pairs.length;

  const handleLeftClick = useCallback((pairId: string) => {
    if (isSubmitted) return;
    setSelectedLeft(prev => prev === pairId ? null : pairId);
  }, [isSubmitted]);

  const handleRightClick = useCallback((pairId: string) => {
    if (isSubmitted || !selectedLeft) return;
    // Connect selectedLeft → this right item
    setConnections(prev => {
      const next = new Map(prev);
      // Remove any existing connection from this left item
      next.set(selectedLeft, pairId);
      // Remove any other left item that was connected to this right item
      for (const [leftId, rightId] of next.entries()) {
        if (rightId === pairId && leftId !== selectedLeft) {
          next.delete(leftId);
        }
      }
      return next;
    });
    setSelectedLeft(null);
  }, [isSubmitted, selectedLeft]);

  const handleSubmit = useCallback(() => {
    setIsSubmitted(true);
    const newResults = new Map<string, boolean>();
    for (const [leftPairId, rightPairId] of connections.entries()) {
      const isCorrect = leftPairId === rightPairId;
      newResults.set(leftPairId, isCorrect);
      // Dispatch each correct match to store (store handles scoring)
      if (isCorrect) {
        onAction?.({ type: 'match_pair', mechanic: 'memory_match', pairId: leftPairId });
      }
    }
    setResults(newResults);
  }, [connections, onAction]);

  const handleRetry = useCallback(() => {
    setConnections(new Map());
    setSelectedLeft(null);
    setIsSubmitted(false);
    setResults(new Map());
    setShowExplanation(null);
  }, []);

  // Get the right pairId connected to a given left pairId
  const getConnectedRight = (leftPairId: string) => connections.get(leftPairId);

  // Check if a right item is connected to any left item
  const isRightConnected = (rightPairId: string) => {
    for (const v of connections.values()) {
      if (v === rightPairId) return true;
    }
    return false;
  };

  // Get line color for a connection
  const getLineColor = (leftPairId: string) => {
    if (!isSubmitted) return '#6366f1'; // indigo
    return results.get(leftPairId) ? '#22c55e' : '#ef4444'; // green or red
  };

  return (
    <div className="w-full max-w-4xl mx-auto p-4">
      {/* Instructions */}
      <div className="mb-4 p-4 bg-gradient-to-r from-amber-50 to-yellow-50 dark:from-amber-900/20 dark:to-yellow-900/20 rounded-xl border border-amber-100 dark:border-amber-800">
        <p className="text-sm text-amber-800 dark:text-amber-200 font-medium">{instructions}</p>
        <p className="text-xs text-amber-600 dark:text-amber-400 mt-1">
          {connections.size}/{pairs.length} connected
        </p>
      </div>

      {/* Two columns with SVG lines */}
      <div ref={containerRef} className="relative flex gap-6 items-start">
        {/* Left column: organ images */}
        <div className="flex-1 flex flex-col gap-3">
          <h3 className="text-sm font-semibold text-gray-600 dark:text-gray-400 mb-1">Organs</h3>
          {shuffledLeft.map((item) => {
            const isSelected = selectedLeft === item.pairId;
            const isConnected = connections.has(item.pairId);
            const result = results.get(item.pairId);
            const borderColor = isSubmitted
              ? (result ? 'border-green-400 bg-green-50 dark:bg-green-900/20' : 'border-red-400 bg-red-50 dark:bg-red-900/20')
              : isSelected
                ? 'border-indigo-500 bg-indigo-50 dark:bg-indigo-900/20 ring-2 ring-indigo-300'
                : isConnected
                  ? 'border-indigo-300 bg-indigo-50/50'
                  : 'border-gray-200 dark:border-gray-600 hover:border-indigo-300';

            return (
              <div
                key={item.pairId}
                ref={(el) => { if (el) leftRefs.current.set(item.pairId, el); }}
                className={`relative rounded-xl border-2 p-3 cursor-pointer transition-all duration-200 ${borderColor}`}
                onClick={() => handleLeftClick(item.pairId)}
              >
                {item.type === 'image' ? (
                  <img src={item.content} alt="" className="w-full h-20 object-contain rounded" />
                ) : (
                  <p className="text-sm font-medium text-gray-800 dark:text-gray-100 text-center">{item.content}</p>
                )}
                {isSubmitted && result !== undefined && (
                  <div className={`absolute -top-2 -right-2 w-6 h-6 rounded-full flex items-center justify-center ${result ? 'bg-green-500' : 'bg-red-500'}`}>
                    {result ? (
                      <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" /></svg>
                    ) : (
                      <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M6 18L18 6M6 6l12 12" /></svg>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>

        {/* SVG connection lines overlay */}
        <svg className="absolute inset-0 w-full h-full pointer-events-none" style={{ zIndex: 1 }}>
          {Array.from(connections.entries()).map(([leftPairId, rightPairId]) => {
            const leftEl = leftRefs.current.get(leftPairId);
            const rightEl = rightRefs.current.get(rightPairId);
            const container = containerRef.current;
            if (!leftEl || !rightEl || !container) return null;

            const containerRect = container.getBoundingClientRect();
            const leftRect = leftEl.getBoundingClientRect();
            const rightRect = rightEl.getBoundingClientRect();

            const x1 = leftRect.right - containerRect.left;
            const y1 = leftRect.top + leftRect.height / 2 - containerRect.top;
            const x2 = rightRect.left - containerRect.left;
            const y2 = rightRect.top + rightRect.height / 2 - containerRect.top;
            const cpOffset = (x2 - x1) * 0.4;

            return (
              <path
                key={`line-${leftPairId}`}
                d={`M ${x1} ${y1} C ${x1 + cpOffset} ${y1}, ${x2 - cpOffset} ${y2}, ${x2} ${y2}`}
                fill="none"
                stroke={getLineColor(leftPairId)}
                strokeWidth={2.5}
                strokeLinecap="round"
              />
            );
          })}
        </svg>

        {/* Right column: function descriptions */}
        <div className="flex-1 flex flex-col gap-3" style={{ zIndex: 2 }}>
          <h3 className="text-sm font-semibold text-gray-600 dark:text-gray-400 mb-1">Functions</h3>
          {shuffledRight.map((item) => {
            const connected = isRightConnected(item.pairId);
            const borderColor = isSubmitted
              ? 'border-gray-300 dark:border-gray-600'
              : connected
                ? 'border-indigo-300 bg-indigo-50/50 dark:bg-indigo-900/10'
                : selectedLeft
                  ? 'border-gray-200 dark:border-gray-600 hover:border-indigo-400 hover:bg-indigo-50/30'
                  : 'border-gray-200 dark:border-gray-600';

            return (
              <div
                key={item.pairId}
                ref={(el) => { if (el) rightRefs.current.set(item.pairId, el); }}
                className={`relative rounded-xl border-2 p-3 cursor-pointer transition-all duration-200 ${borderColor}`}
                onClick={() => handleRightClick(item.pairId)}
              >
                {item.type === 'image' ? (
                  <img src={item.content} alt="" className="w-full h-20 object-contain rounded" />
                ) : (
                  <p className="text-sm text-gray-700 dark:text-gray-200 leading-snug">{item.content}</p>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Submit / Retry buttons */}
      <div className="mt-6 flex justify-center gap-3">
        {!isSubmitted && allConnected && (
          <motion.button
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            onClick={handleSubmit}
            className="px-6 py-3 bg-indigo-600 hover:bg-indigo-700 text-white font-semibold rounded-xl shadow-lg transition-colors"
          >
            Check Matches
          </motion.button>
        )}
        {isSubmitted && (
          <motion.button
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            onClick={handleRetry}
            className="px-6 py-3 bg-gray-200 hover:bg-gray-300 dark:bg-gray-700 dark:hover:bg-gray-600 text-gray-800 dark:text-gray-200 font-semibold rounded-xl shadow transition-colors"
          >
            Try Again
          </motion.button>
        )}
      </div>

      {/* Results summary */}
      {isSubmitted && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="mt-4 space-y-2"
        >
          {pairs.map(pair => {
            const isCorrect = results.get(pair.id);
            return (
              <div
                key={pair.id}
                className={`p-3 rounded-lg border ${isCorrect ? 'bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800' : 'bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800'}`}
              >
                <div className="flex items-center gap-2">
                  <span className={`text-sm font-medium ${isCorrect ? 'text-green-700 dark:text-green-300' : 'text-red-700 dark:text-red-300'}`}>
                    {isCorrect ? 'Correct' : 'Incorrect'}
                  </span>
                  <span className="text-sm text-gray-600 dark:text-gray-400">
                    — {pair.explanation}
                  </span>
                </div>
              </div>
            );
          })}
        </motion.div>
      )}
    </div>
  );
}

// ─── Main Component ─────────────────────────────────────────────────
export function EnhancedMemoryMatch({
  config,
  storeProgress,
  onAction,
}: EnhancedMemoryMatchProps) {
  // Guard: config may be minimal/empty from registry fallback
  if (!config || !config.pairs || config.pairs.length === 0) {
    return (
      <div className="p-4 text-center text-gray-500">
        <p>Memory match configuration is missing or has no pairs.</p>
      </div>
    );
  }

  const {
    pairs,
    gridSize,
    flipDurationMs = 400,
    showAttemptsCounter = true,
    instructions = 'Find all matching pairs by flipping cards.',
    card_back_style = 'gradient',
    matched_card_behavior = 'checkmark',
    show_explanation_on_match = true,
    game_variant,
  } = config;

  // Route to ColumnMatchMode if game_variant is column_match
  if (game_variant === 'column_match') {
    return (
      <ColumnMatchMode
        pairs={pairs}
        instructions={instructions}
        show_explanation_on_match={show_explanation_on_match}
        onAction={onAction}
      />
    );
  }

  // Build card instances (2 per pair, shuffled)
  const cards = useMemo(() => {
    const allCards: CardData[] = [];
    pairs.forEach((pair) => {
      allCards.push({
        instanceId: `${pair.id}_front`,
        pairId: pair.id,
        content: pair.front,
        type: pair.frontType,
        side: 'front',
        explanation: pair.explanation,
      });
      allCards.push({
        instanceId: `${pair.id}_back`,
        pairId: pair.id,
        content: pair.back,
        type: pair.backType,
        side: 'back',
        explanation: pair.explanation,
      });
    });
    // Shuffle
    for (let i = allCards.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [allCards[i], allCards[j]] = [allCards[j], allCards[i]];
    }
    return allCards;
  }, [pairs]);

  // Layer 3: Initialize from storeProgress for restoration
  const restoredMatchedIds = useMemo(
    () => new Set(storeProgress?.matchedPairIds ?? []),
    // Only compute once on mount — storeProgress is the seed, local state takes over
    // eslint-disable-next-line react-hooks/exhaustive-deps
    []
  );

  const [cardStates, setCardStates] = useState<Record<string, CardState>>(() => {
    const states: Record<string, CardState> = {};
    cards.forEach((c) => {
      states[c.instanceId] = restoredMatchedIds.has(c.pairId) ? 'matched' : 'face_down';
    });
    return states;
  });
  const [flippedCards, setFlippedCards] = useState<string[]>([]);
  const [matchedPairIds, setMatchedPairIds] = useState<Set<string>>(restoredMatchedIds);
  const [attempts, setAttempts] = useState(storeProgress?.attempts ?? 0);
  const [showParticles, setShowParticles] = useState(false);
  const [currentExplanation, setCurrentExplanation] = useState<string | null>(null);
  const isCheckingRef = useRef(false);

  // Grid dimensions — gridSize can be [number, number] array or "4x3" string from backend
  const [cols, rows] = useMemo(() => {
    if (gridSize) {
      if (Array.isArray(gridSize) && gridSize.length >= 2) {
        return [Number(gridSize[0]) || 4, Number(gridSize[1]) || 3];
      }
      if (typeof gridSize === 'string') {
        const parts = (gridSize as string).split('x').map(Number);
        if (parts.length >= 2 && parts[0] > 0 && parts[1] > 0) {
          return [parts[0], parts[1]];
        }
      }
    }
    const total = cards.length;
    if (total === 0) return [1, 1];
    const c = Math.ceil(Math.sqrt(total));
    const r = Math.ceil(total / c);
    return [c, r];
  }, [cards.length, gridSize]);

  const handleCardClick = useCallback((instanceId: string) => {
    if (isCheckingRef.current) return;
    if (cardStates[instanceId] !== 'face_down') return;
    if (flippedCards.length >= 2) return;

    // Flip card
    setCardStates((prev) => ({ ...prev, [instanceId]: 'face_up' }));
    const newFlipped = [...flippedCards, instanceId];
    setFlippedCards(newFlipped);

    // Check for match when 2 cards are flipped
    if (newFlipped.length === 2) {
      isCheckingRef.current = true;
      setAttempts((prev) => prev + 1);
      onAction?.({ type: 'memory_attempt', mechanic: 'memory_match' });

      const card1 = cards.find((c) => c.instanceId === newFlipped[0]);
      const card2 = cards.find((c) => c.instanceId === newFlipped[1]);

      if (card1 && card2 && card1.pairId === card2.pairId) {
        // Match!
        setTimeout(() => {
          setCardStates((prev) => ({
            ...prev,
            [newFlipped[0]]: 'matched',
            [newFlipped[1]]: 'matched',
          }));
          setMatchedPairIds((prev) => new Set([...prev, card1.pairId]));
          setFlippedCards([]);
          setShowParticles(true);
          setTimeout(() => setShowParticles(false), 700);

          if (show_explanation_on_match && card1.explanation) {
            setCurrentExplanation(card1.explanation);
          }

          onAction?.({ type: 'match_pair', mechanic: 'memory_match', pairId: card1.pairId });
          isCheckingRef.current = false;
        }, 500);
      } else {
        // Mismatch: flip back after delay
        setTimeout(() => {
          setCardStates((prev) => ({
            ...prev,
            [newFlipped[0]]: 'face_down',
            [newFlipped[1]]: 'face_down',
          }));
          setFlippedCards([]);
          isCheckingRef.current = false;
        }, 1000);
      }
    }
  }, [cardStates, flippedCards, cards, onAction, show_explanation_on_match]);

  // Completion is handled by store via recordMemoryMatch action.
  // No local completion detection needed.

  return (
    <div className="w-full max-w-3xl mx-auto p-4">
      {/* Instructions */}
      <div className="mb-4 p-4 bg-gradient-to-r from-amber-50 to-yellow-50 dark:from-amber-900/20 dark:to-yellow-900/20 rounded-xl border border-amber-100 dark:border-amber-800">
        <p className="text-sm text-amber-800 dark:text-amber-200 font-medium">{instructions}</p>
        <p className="text-xs text-amber-600 dark:text-amber-400 mt-1">
          {pairs.length} pairs to find
        </p>
      </div>

      {/* Stats bar */}
      {showAttemptsCounter && (
        <StatsBar
          matched={matchedPairIds.size}
          total={pairs.length}
          attempts={attempts}
        />
      )}

      {/* Card grid */}
      <div
        className="grid gap-3 relative"
        style={{ gridTemplateColumns: `repeat(${cols}, 1fr)` }}
      >
        {cards.map((card) => (
          <FlipCard
            key={card.instanceId}
            card={card}
            state={cardStates[card.instanceId]}
            onClick={handleCardClick}
            flipDuration={flipDurationMs}
            cardBackStyle={card_back_style}
            matchedBehavior={matched_card_behavior}
          />
        ))}

        {/* Particles */}
        <MatchParticles show={showParticles} />
      </div>

      {/* Completion message */}
      <AnimatePresence>
        {matchedPairIds.size === pairs.length && pairs.length > 0 && (
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            className="mt-6 p-4 bg-green-50 dark:bg-green-900/20 border-2 border-green-300 dark:border-green-700 rounded-xl text-center"
          >
            <p className="text-lg font-bold text-green-800 dark:text-green-200">🎉 All pairs matched!</p>
            <p className="text-sm text-green-600 dark:text-green-400 mt-1">
              Completed in {attempts} attempts
            </p>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Explanation overlay */}
      {currentExplanation && (
        <ExplanationOverlay
          explanation={currentExplanation}
          show={!!currentExplanation}
          onDismiss={() => setCurrentExplanation(null)}
          durationMs={3000}
        />
      )}
    </div>
  );
}

export default EnhancedMemoryMatch;
