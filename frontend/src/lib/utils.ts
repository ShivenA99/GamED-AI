/**
 * Utility Functions
 *
 * Shared utility functions used across the application.
 */
import { type ClassValue, clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'

/**
 * Merges class names with Tailwind CSS conflict resolution.
 * Combines clsx for conditional classes with tailwind-merge for deduplication.
 *
 * @param inputs - Class values (strings, objects, arrays, conditionals)
 * @returns Merged class string with Tailwind conflicts resolved
 *
 * @example
 * ```tsx
 * cn('px-4 py-2', 'px-6')           // → 'py-2 px-6' (px-6 wins)
 * cn('text-red-500', isActive && 'text-blue-500')
 * cn(baseStyles, variantStyles, className)
 * ```
 */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}
