/**
 * Skeleton Component
 *
 * A placeholder loading component that displays a pulsing animation.
 * Use to indicate content is loading and improve perceived performance.
 *
 * @example
 * ```tsx
 * // Text skeleton
 * <Skeleton className="h-4 w-48" />
 *
 * // Card skeleton
 * <Skeleton className="h-32 w-full rounded-xl" />
 *
 * // Avatar skeleton
 * <Skeleton className="h-12 w-12 rounded-full" />
 * ```
 */
import { cn } from '@/lib/utils'

/**
 * Skeleton placeholder component with pulse animation.
 * Apply width/height via className to match the content being loaded.
 */
function Skeleton({
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn('animate-pulse rounded-md bg-muted', className)}
      aria-hidden="true"
      {...props}
    />
  )
}

export { Skeleton }
