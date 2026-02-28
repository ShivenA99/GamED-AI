'use client';

import React, { useEffect, useCallback, useRef } from 'react';

// Reference counter for shared keyboard nav styles
let keyboardNavStyleRefCount = 0;

/**
 * Keyboard navigation configuration
 */
export interface KeyboardNavConfig {
  /** Enable keyboard navigation (default: true) */
  enabled?: boolean;
  /** Focusable element selector */
  focusableSelector?: string;
  /** Wrap around when reaching ends */
  wrapAround?: boolean;
  /** Custom key handlers */
  customHandlers?: Record<string, (event: KeyboardEvent) => void>;
}

/**
 * Props for KeyboardNav component
 */
export interface KeyboardNavProps extends KeyboardNavConfig {
  /** Container element ref */
  containerRef?: React.RefObject<HTMLElement>;
  /** Children to wrap */
  children: React.ReactNode;
  /** Callback when focus changes */
  onFocusChange?: (element: HTMLElement, index: number) => void;
  /** Callback when element is activated (Enter/Space) */
  onActivate?: (element: HTMLElement, index: number) => void;
  /** Custom class name */
  className?: string;
}

const DEFAULT_FOCUSABLE_SELECTOR =
  'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"]), [data-focusable="true"]';

/**
 * KeyboardNav - Provides keyboard navigation for game elements
 *
 * Supports:
 * - Arrow key navigation between focusable elements
 * - Enter/Space activation
 * - Tab navigation with focus management
 * - Escape key for cancel/close
 * - Custom key handlers
 */
export function KeyboardNav({
  enabled = true,
  focusableSelector = DEFAULT_FOCUSABLE_SELECTOR,
  wrapAround = true,
  customHandlers = {},
  containerRef,
  children,
  onFocusChange,
  onActivate,
  className = '',
}: KeyboardNavProps) {
  const internalRef = useRef<HTMLDivElement>(null);
  const ref = containerRef || internalRef;
  const currentIndexRef = useRef<number>(-1);

  // Get all focusable elements
  const getFocusableElements = useCallback((): HTMLElement[] => {
    if (!ref.current) return [];
    return Array.from(ref.current.querySelectorAll(focusableSelector));
  }, [ref, focusableSelector]);

  // Focus element at index
  const focusAtIndex = useCallback(
    (index: number) => {
      const elements = getFocusableElements();
      if (elements.length === 0) return;

      let targetIndex = index;
      if (wrapAround) {
        targetIndex = ((index % elements.length) + elements.length) % elements.length;
      } else {
        targetIndex = Math.max(0, Math.min(index, elements.length - 1));
      }

      const element = elements[targetIndex];
      if (element) {
        element.focus();
        currentIndexRef.current = targetIndex;
        onFocusChange?.(element, targetIndex);
      }
    },
    [getFocusableElements, wrapAround, onFocusChange]
  );

  // Handle keyboard events
  const handleKeyDown = useCallback(
    (event: KeyboardEvent) => {
      if (!enabled) return;

      // Check for custom handler first
      if (customHandlers[event.key]) {
        customHandlers[event.key](event);
        return;
      }

      const elements = getFocusableElements();
      const currentIndex = elements.findIndex((el) => el === document.activeElement);

      switch (event.key) {
        case 'ArrowDown':
        case 'ArrowRight':
          event.preventDefault();
          focusAtIndex(currentIndex + 1);
          break;

        case 'ArrowUp':
        case 'ArrowLeft':
          event.preventDefault();
          focusAtIndex(currentIndex - 1);
          break;

        case 'Home':
          event.preventDefault();
          focusAtIndex(0);
          break;

        case 'End':
          event.preventDefault();
          focusAtIndex(elements.length - 1);
          break;

        case 'Enter':
        case ' ':
          if (document.activeElement && elements.includes(document.activeElement as HTMLElement)) {
            event.preventDefault();
            onActivate?.(document.activeElement as HTMLElement, currentIndex);
            // Simulate click for interactive elements
            (document.activeElement as HTMLElement).click();
          }
          break;

        case 'Escape':
          // Blur current element
          (document.activeElement as HTMLElement)?.blur();
          break;
      }
    },
    [enabled, customHandlers, getFocusableElements, focusAtIndex, onActivate]
  );

  // Set up event listeners
  useEffect(() => {
    if (!enabled || !ref.current) return;

    const container = ref.current;
    container.addEventListener('keydown', handleKeyDown);

    return () => {
      container.removeEventListener('keydown', handleKeyDown);
    };
  }, [enabled, ref, handleKeyDown]);

  // Add focus visible styles with cleanup (reference counting for shared styles)
  useEffect(() => {
    if (!enabled) return;

    const styleId = 'keyboard-nav-styles';
    let styleElement = document.getElementById(styleId) as HTMLStyleElement | null;

    // Create style element if it doesn't exist
    if (!styleElement) {
      styleElement = document.createElement('style');
      styleElement.id = styleId;
      styleElement.textContent = `
        [data-keyboard-nav] *:focus {
          outline: 2px solid #3b82f6;
          outline-offset: 2px;
        }
        [data-keyboard-nav] *:focus:not(:focus-visible) {
          outline: none;
        }
        [data-keyboard-nav] *:focus-visible {
          outline: 2px solid #3b82f6;
          outline-offset: 2px;
        }
      `;
      document.head.appendChild(styleElement);
    }

    // Increment reference count
    keyboardNavStyleRefCount++;

    // Cleanup: decrement reference count and remove style when no more users
    return () => {
      keyboardNavStyleRefCount--;
      if (keyboardNavStyleRefCount === 0) {
        const style = document.getElementById(styleId);
        if (style) {
          style.remove();
        }
      }
    };
  }, [enabled]);

  if (!containerRef) {
    return (
      <div
        ref={internalRef}
        className={className}
        data-keyboard-nav={enabled ? 'true' : undefined}
      >
        {children}
      </div>
    );
  }

  return <>{children}</>;
}

/**
 * Hook for keyboard navigation functionality
 */
export function useKeyboardNav(config: KeyboardNavConfig = {}) {
  const { enabled = true, focusableSelector = DEFAULT_FOCUSABLE_SELECTOR, customHandlers = {} } =
    config;
  const containerRef = useRef<HTMLDivElement>(null);

  const getFocusableElements = useCallback((): HTMLElement[] => {
    if (!containerRef.current) return [];
    return Array.from(containerRef.current.querySelectorAll(focusableSelector));
  }, [focusableSelector]);

  const focusFirst = useCallback(() => {
    const elements = getFocusableElements();
    if (elements.length > 0) {
      elements[0].focus();
    }
  }, [getFocusableElements]);

  const focusLast = useCallback(() => {
    const elements = getFocusableElements();
    if (elements.length > 0) {
      elements[elements.length - 1].focus();
    }
  }, [getFocusableElements]);

  const focusNext = useCallback(() => {
    const elements = getFocusableElements();
    const currentIndex = elements.findIndex((el) => el === document.activeElement);
    const nextIndex = (currentIndex + 1) % elements.length;
    if (elements[nextIndex]) {
      elements[nextIndex].focus();
    }
  }, [getFocusableElements]);

  const focusPrevious = useCallback(() => {
    const elements = getFocusableElements();
    const currentIndex = elements.findIndex((el) => el === document.activeElement);
    const prevIndex = (currentIndex - 1 + elements.length) % elements.length;
    if (elements[prevIndex]) {
      elements[prevIndex].focus();
    }
  }, [getFocusableElements]);

  return {
    containerRef,
    focusFirst,
    focusLast,
    focusNext,
    focusPrevious,
    getFocusableElements,
  };
}

export default KeyboardNav;
