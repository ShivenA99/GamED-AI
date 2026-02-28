/**
 * Hook for detecting user's reduced motion preference.
 *
 * Respects the `prefers-reduced-motion` media query to provide
 * accessible animations that don't trigger motion sensitivity issues.
 *
 * Usage:
 *   const reducedMotion = useReducedMotion();
 *   const duration = reducedMotion ? 0 : 300;
 */
import { useState, useEffect } from 'react';

export function useReducedMotion(): boolean {
  const [prefersReducedMotion, setPrefersReducedMotion] = useState(false);

  useEffect(() => {
    // Check if window is available (SSR safety)
    if (typeof window === 'undefined') return;

    const mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
    setPrefersReducedMotion(mediaQuery.matches);

    const handler = (event: MediaQueryListEvent) => {
      setPrefersReducedMotion(event.matches);
    };

    // Modern browsers
    mediaQuery.addEventListener('change', handler);

    return () => {
      mediaQuery.removeEventListener('change', handler);
    };
  }, []);

  return prefersReducedMotion;
}

export default useReducedMotion;
