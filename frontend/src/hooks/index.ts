/**
 * Custom React Hooks
 *
 * Shared hooks for accessibility and animation control.
 *
 * @example
 * ```tsx
 * import { useReducedMotion, useAnimationDuration } from '@/hooks'
 *
 * const MyComponent = () => {
 *   const prefersReducedMotion = useReducedMotion()
 *   const duration = useAnimationDuration(300)
 *
 *   return <div style={{ transitionDuration: `${duration}ms` }} />
 * }
 * ```
 */
export {
  useReducedMotion,
  useAnimationDuration,
  useAnimationClass,
} from './useReducedMotion'
