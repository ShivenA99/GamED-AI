'use client'

import { useState, useEffect } from 'react'

/**
 * Hook to detect if the user prefers reduced motion
 * Respects the prefers-reduced-motion media query for accessibility
 *
 * @returns boolean - true if user prefers reduced motion
 */
export function useReducedMotion(): boolean {
  const [prefersReducedMotion, setPrefersReducedMotion] = useState(false)

  useEffect(() => {
    // Check if window is available (client-side)
    if (typeof window === 'undefined') return

    const mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)')

    // Set initial value
    setPrefersReducedMotion(mediaQuery.matches)

    // Listen for changes
    const handleChange = (event: MediaQueryListEvent) => {
      setPrefersReducedMotion(event.matches)
    }

    // Modern browsers
    mediaQuery.addEventListener('change', handleChange)

    return () => {
      mediaQuery.removeEventListener('change', handleChange)
    }
  }, [])

  return prefersReducedMotion
}

/**
 * Hook that returns animation duration based on user preference
 * Returns 0 if user prefers reduced motion, otherwise returns the provided duration
 *
 * @param duration - The normal animation duration in ms
 * @returns number - 0 or the provided duration
 */
export function useAnimationDuration(duration: number): number {
  const prefersReducedMotion = useReducedMotion()
  return prefersReducedMotion ? 0 : duration
}

/**
 * Hook that returns animation class based on user preference
 * Returns empty string if user prefers reduced motion
 *
 * @param animationClass - The animation class to conditionally apply
 * @returns string - empty string or the provided class
 */
export function useAnimationClass(animationClass: string): string {
  const prefersReducedMotion = useReducedMotion()
  return prefersReducedMotion ? '' : animationClass
}
