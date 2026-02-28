/**
 * Theme Provider Component
 *
 * Wraps the application with next-themes provider for dark mode support.
 * Configured with class-based theme switching for Tailwind CSS compatibility.
 *
 * Features:
 * - System preference detection via `enableSystem`
 * - Persists preference to localStorage
 * - Uses class attribute for Tailwind dark: variants
 * - Disables transitions during theme change to prevent flash
 *
 * @example
 * ```tsx
 * // In layout.tsx
 * <ThemeProvider>
 *   <html>
 *     <body>{children}</body>
 *   </html>
 * </ThemeProvider>
 * ```
 */
'use client'

import { ThemeProvider as NextThemesProvider } from 'next-themes'
import { type ThemeProviderProps } from 'next-themes'

/**
 * Theme provider wrapper with sensible defaults for Tailwind CSS dark mode.
 * @param props - next-themes ThemeProviderProps, can override defaults
 */
export function ThemeProvider({ children, ...props }: ThemeProviderProps) {
  return (
    <NextThemesProvider
      attribute="class"
      defaultTheme="system"
      enableSystem
      disableTransitionOnChange
      {...props}
    >
      {children}
    </NextThemesProvider>
  )
}
