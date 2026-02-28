'use client';

import React, { createContext, useContext, useState, useCallback, useRef, useEffect } from 'react';

/**
 * Announcement priority levels
 */
export type AnnouncementPriority = 'polite' | 'assertive';

/**
 * Announcement message structure
 */
export interface Announcement {
  id: string;
  message: string;
  priority: AnnouncementPriority;
  timestamp: number;
}

/**
 * Context value for screen reader announcements
 */
interface AnnouncementContextValue {
  /** Announce a message to screen readers */
  announce: (message: string, priority?: AnnouncementPriority) => void;
  /** Announce game action (correct/incorrect placement, etc.) */
  announceGameAction: (action: GameAction) => void;
  /** Clear all announcements */
  clearAnnouncements: () => void;
}

/**
 * Game action types for contextual announcements
 */
export type GameAction =
  | { type: 'label_placed'; labelText: string; zoneName: string; isCorrect: boolean }
  | { type: 'label_removed'; labelText: string }
  | { type: 'zone_revealed'; zoneName: string; reason?: string }
  | { type: 'zone_completed'; zoneName: string }
  | { type: 'hint_shown'; hintText: string }
  | { type: 'score_changed'; newScore: number; maxScore: number }
  | { type: 'game_started'; title: string; totalZones: number }
  | { type: 'game_completed'; score: number; maxScore: number }
  | { type: 'timer_warning'; secondsRemaining: number }
  | { type: 'timer_expired' }
  | { type: 'undo'; description: string }
  | { type: 'redo'; description: string }
  | { type: 'custom'; message: string; priority?: AnnouncementPriority };

const AnnouncementContext = createContext<AnnouncementContextValue | null>(null);

/**
 * Generate announcement text for game actions
 */
function getAnnouncementForAction(action: GameAction): { message: string; priority: AnnouncementPriority } {
  switch (action.type) {
    case 'label_placed':
      return {
        message: action.isCorrect
          ? `Correct! ${action.labelText} placed on ${action.zoneName}.`
          : `Incorrect. ${action.labelText} does not belong on ${action.zoneName}. Try again.`,
        priority: action.isCorrect ? 'polite' : 'assertive',
      };

    case 'label_removed':
      return {
        message: `${action.labelText} removed and returned to label tray.`,
        priority: 'polite',
      };

    case 'zone_revealed':
      return {
        message: action.reason
          ? `New zone available: ${action.zoneName}. ${action.reason}`
          : `New zone available: ${action.zoneName}.`,
        priority: 'polite',
      };

    case 'zone_completed':
      return {
        message: `${action.zoneName} completed successfully.`,
        priority: 'polite',
      };

    case 'hint_shown':
      return {
        message: `Hint: ${action.hintText}`,
        priority: 'polite',
      };

    case 'score_changed':
      return {
        message: `Score: ${action.newScore} out of ${action.maxScore}.`,
        priority: 'polite',
      };

    case 'game_started':
      return {
        message: `Game started: ${action.title}. ${action.totalZones} zones to complete.`,
        priority: 'assertive',
      };

    case 'game_completed':
      const percentage = Math.round((action.score / action.maxScore) * 100);
      return {
        message: `Congratulations! Game completed with ${action.score} out of ${action.maxScore} points. That's ${percentage} percent.`,
        priority: 'assertive',
      };

    case 'timer_warning':
      return {
        message: `Warning: ${action.secondsRemaining} seconds remaining.`,
        priority: 'assertive',
      };

    case 'timer_expired':
      return {
        message: 'Time is up!',
        priority: 'assertive',
      };

    case 'undo':
      return {
        message: `Undone: ${action.description}`,
        priority: 'polite',
      };

    case 'redo':
      return {
        message: `Redone: ${action.description}`,
        priority: 'polite',
      };

    case 'custom':
      return {
        message: action.message,
        priority: action.priority || 'polite',
      };

    default:
      return { message: '', priority: 'polite' };
  }
}

/**
 * Provider for screen reader announcements
 */
export function AnnouncementProvider({ children }: { children: React.ReactNode }) {
  const [politeAnnouncement, setPoliteAnnouncement] = useState('');
  const [assertiveAnnouncement, setAssertiveAnnouncement] = useState('');
  const politeTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const assertiveTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Clear announcement after a delay
  const clearAfterDelay = useCallback((priority: AnnouncementPriority) => {
    const timeoutRef = priority === 'polite' ? politeTimeoutRef : assertiveTimeoutRef;
    const setter = priority === 'polite' ? setPoliteAnnouncement : setAssertiveAnnouncement;

    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }

    // 3 seconds is more reliable for screen readers to announce longer messages
    timeoutRef.current = setTimeout(() => {
      setter('');
    }, 3000);
  }, []);

  // Announce message
  const announce = useCallback(
    (message: string, priority: AnnouncementPriority = 'polite') => {
      if (!message) return;

      if (priority === 'polite') {
        setPoliteAnnouncement(message);
      } else {
        setAssertiveAnnouncement(message);
      }

      clearAfterDelay(priority);
    },
    [clearAfterDelay]
  );

  // Announce game action
  const announceGameAction = useCallback(
    (action: GameAction) => {
      const { message, priority } = getAnnouncementForAction(action);
      if (message) {
        announce(message, priority);
      }
    },
    [announce]
  );

  // Clear all announcements
  const clearAnnouncements = useCallback(() => {
    setPoliteAnnouncement('');
    setAssertiveAnnouncement('');
    if (politeTimeoutRef.current) clearTimeout(politeTimeoutRef.current);
    if (assertiveTimeoutRef.current) clearTimeout(assertiveTimeoutRef.current);
  }, []);

  // Cleanup timeouts on unmount
  useEffect(() => {
    return () => {
      if (politeTimeoutRef.current) clearTimeout(politeTimeoutRef.current);
      if (assertiveTimeoutRef.current) clearTimeout(assertiveTimeoutRef.current);
    };
  }, []);

  return (
    <AnnouncementContext.Provider value={{ announce, announceGameAction, clearAnnouncements }}>
      {children}

      {/* ARIA live regions */}
      <div
        role="status"
        aria-live="polite"
        aria-atomic="true"
        className="sr-only"
      >
        {politeAnnouncement}
      </div>
      <div
        role="alert"
        aria-live="assertive"
        aria-atomic="true"
        className="sr-only"
      >
        {assertiveAnnouncement}
      </div>

      {/* Visually hidden styles */}
      <style jsx>{`
        .sr-only {
          position: absolute;
          width: 1px;
          height: 1px;
          padding: 0;
          margin: -1px;
          overflow: hidden;
          clip: rect(0, 0, 0, 0);
          white-space: nowrap;
          border: 0;
        }
      `}</style>
    </AnnouncementContext.Provider>
  );
}

/**
 * Hook for using screen reader announcements
 */
export function useAnnouncements(): AnnouncementContextValue {
  const context = useContext(AnnouncementContext);
  if (!context) {
    // Return no-op functions if not within provider
    return {
      announce: () => {},
      announceGameAction: () => {},
      clearAnnouncements: () => {},
    };
  }
  return context;
}

/**
 * Component for making static announcements on mount
 */
export function Announce({
  message,
  priority = 'polite',
}: {
  message: string;
  priority?: AnnouncementPriority;
}) {
  const { announce } = useAnnouncements();

  useEffect(() => {
    if (message) {
      announce(message, priority);
    }
  }, [message, priority, announce]);

  return null;
}

export default AnnouncementProvider;
