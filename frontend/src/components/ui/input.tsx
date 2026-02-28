/**
 * Input Component
 *
 * A styled text input component with error state support.
 * Built with consistent focus rings and dark mode compatibility.
 *
 * @example
 * ```tsx
 * <Input type="email" placeholder="Enter email" />
 * <Input type="password" error={!isValid} />
 * <Input disabled placeholder="Disabled input" />
 * ```
 */
import * as React from 'react'

import { cn } from '@/lib/utils'

/**
 * Input component props
 * @property {boolean} error - When true, displays error styling (red border/ring)
 */
export interface InputProps
  extends React.InputHTMLAttributes<HTMLInputElement> {
  error?: boolean
}

/** Styled input with error state support and consistent dark mode styling */
const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, type, error, ...props }, ref) => {
    return (
      <input
        type={type}
        className={cn(
          'flex h-10 w-full rounded-lg border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium file:text-foreground placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 dark:ring-offset-gray-900',
          error && 'border-destructive focus-visible:ring-destructive',
          className
        )}
        ref={ref}
        {...props}
      />
    )
  }
)
Input.displayName = 'Input'

export { Input }
