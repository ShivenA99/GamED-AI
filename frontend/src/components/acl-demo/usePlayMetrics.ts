'use client';

import { useCallback, useEffect, useRef, useState } from 'react';

export interface PlayMetrics {
  gameId: string;
  mode: 'learn' | 'test';
  startTime: string;
  endTime: string | null;
  elapsedSeconds: number;
  score: number;
  maxScore: number;
  hintsUsed: number;
  incorrectAttempts: number;
  interactionCount: number;
  completed: boolean;
}

const STORAGE_KEY = 'acl-demo-play-metrics';

function loadAllMetrics(): Record<string, PlayMetrics[]> {
  if (typeof window === 'undefined') return {};
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : {};
  } catch {
    return {};
  }
}

function saveAllMetrics(data: Record<string, PlayMetrics[]>) {
  if (typeof window === 'undefined') return;
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
  } catch {
    // localStorage full or unavailable — silently ignore
  }
}

export function usePlayMetrics(gameId: string, mode: 'learn' | 'test') {
  const startTimeRef = useRef(new Date().toISOString());
  const [metrics, setMetrics] = useState<PlayMetrics>({
    gameId,
    mode,
    startTime: startTimeRef.current,
    endTime: null,
    elapsedSeconds: 0,
    score: 0,
    maxScore: 0,
    hintsUsed: 0,
    incorrectAttempts: 0,
    interactionCount: 0,
    completed: false,
  });

  // Timer
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    timerRef.current = setInterval(() => {
      setMetrics(prev => ({
        ...prev,
        elapsedSeconds: Math.floor((Date.now() - new Date(prev.startTime).getTime()) / 1000),
      }));
    }, 1000);

    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, []);

  const recordInteraction = useCallback(() => {
    setMetrics(prev => ({ ...prev, interactionCount: prev.interactionCount + 1 }));
  }, []);

  const recordHint = useCallback(() => {
    setMetrics(prev => ({ ...prev, hintsUsed: prev.hintsUsed + 1 }));
  }, []);

  const recordIncorrect = useCallback(() => {
    setMetrics(prev => ({ ...prev, incorrectAttempts: prev.incorrectAttempts + 1 }));
  }, []);

  const completeGame = useCallback((score: number, maxScore: number) => {
    const endTime = new Date().toISOString();
    const elapsed = Math.floor((Date.now() - new Date(startTimeRef.current).getTime()) / 1000);

    if (timerRef.current) clearInterval(timerRef.current);

    const finalMetrics: PlayMetrics = {
      gameId,
      mode,
      startTime: startTimeRef.current,
      endTime,
      elapsedSeconds: elapsed,
      score,
      maxScore,
      hintsUsed: metrics.hintsUsed,
      incorrectAttempts: metrics.incorrectAttempts,
      interactionCount: metrics.interactionCount,
      completed: true,
    };

    setMetrics(finalMetrics);

    // Persist to localStorage
    const all = loadAllMetrics();
    if (!all[gameId]) all[gameId] = [];
    all[gameId].push(finalMetrics);
    saveAllMetrics(all);

    return finalMetrics;
  }, [gameId, mode, metrics.hintsUsed, metrics.incorrectAttempts, metrics.interactionCount]);

  return {
    metrics,
    recordInteraction,
    recordHint,
    recordIncorrect,
    completeGame,
  };
}

/** Get all saved play metrics for the metrics display */
export function getAllPlayMetrics(): Record<string, PlayMetrics[]> {
  return loadAllMetrics();
}

/** Get best score for a specific game */
export function getBestScore(gameId: string): PlayMetrics | null {
  const all = loadAllMetrics();
  const entries = all[gameId];
  if (!entries || entries.length === 0) return null;
  return entries.reduce((best, cur) =>
    cur.score > best.score ? cur : best
  );
}
