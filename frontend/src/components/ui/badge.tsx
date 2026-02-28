/**
 * Badge Component
 *
 * A small status indicator or label component with semantic color variants.
 * Commonly used for displaying status, categories, or counts.
 *
 * @example
 * ```tsx
 * <Badge variant="success">Completed</Badge>
 * <Badge variant="error">Failed</Badge>
 * <Badge variant="info">In Progress</Badge>
 * ```
 */
import * as React from 'react'
import { cva, type VariantProps } from 'class-variance-authority'

import { cn } from '@/lib/utils'

/** Badge style variants - semantic colors for different states */
const badgeVariants = cva(
  'inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2',
  {
    variants: {
      variant: {
        default:
          'border-transparent bg-primary text-primary-foreground shadow hover:bg-primary/80',
        secondary:
          'border-transparent bg-secondary text-secondary-foreground hover:bg-secondary/80',
        destructive:
          'border-transparent bg-destructive text-destructive-foreground shadow hover:bg-destructive/80',
        outline: 'text-foreground',
        success:
          'border-transparent bg-success-bg text-success dark:bg-success/20 dark:text-success',
        error:
          'border-transparent bg-error-bg text-error dark:bg-error/20 dark:text-error',
        warning:
          'border-transparent bg-warning-bg text-warning dark:bg-warning/20 dark:text-warning',
        info:
          'border-transparent bg-info-bg text-info dark:bg-info/20 dark:text-info',
        neutral:
          'border-transparent bg-muted text-muted-foreground',
      },
    },
    defaultVariants: {
      variant: 'default',
    },
  }
)

/** Badge component props */
export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

/**
 * Badge component for displaying status indicators or labels.
 * Supports semantic variants: success, error, warning, info, neutral.
 */
function Badge({ className, variant, ...props }: BadgeProps) {
  return (
    <div className={cn(badgeVariants({ variant }), className)} {...props} />
  )
}

export { Badge, badgeVariants }
