'use client'

import { CSSProperties, forwardRef, useCallback, useMemo, ElementType } from 'react'
import { FixedSizeList as List, ListChildComponentProps } from 'react-window'
import { cn } from '@/lib/utils'

/**
 * VirtualizedList - A performant virtualized list component
 * Use this for rendering large lists (100+ items) with consistent item heights.
 *
 * @example
 * ```tsx
 * <VirtualizedList
 *   items={logs}
 *   height={600}
 *   itemSize={64}
 *   renderItem={(item, index, style) => (
 *     <div style={style} key={item.id}>
 *       {item.message}
 *     </div>
 *   )}
 * />
 * ```
 */

export interface VirtualizedListProps<T> {
  /** Array of items to render */
  items: T[]
  /** Total height of the list container in pixels */
  height: number
  /** Height of each item in pixels (must be consistent) */
  itemSize: number
  /** Width of the list container (default: 100%) */
  width?: string | number
  /** Render function for each item */
  renderItem: (item: T, index: number, style: CSSProperties) => React.ReactNode
  /** Custom class name for the container */
  className?: string
  /** Overscan count - number of items to render before/after visible area */
  overscanCount?: number
  /** Unique key extractor function */
  getKey?: (item: T, index: number) => string | number
  /** Callback when scroll position changes */
  onScroll?: (scrollOffset: number) => void
  /** Initial scroll offset */
  initialScrollOffset?: number
}

interface ItemData<T> {
  items: T[]
  renderItem: (item: T, index: number, style: CSSProperties) => React.ReactNode
  getKey?: (item: T, index: number) => string | number
}

function Row<T>({ index, style, data }: ListChildComponentProps<ItemData<T>>) {
  const { items, renderItem, getKey } = data
  const item = items[index]

  // Generate key if getKey is provided
  const key = getKey ? getKey(item, index) : index

  return (
    <div key={key}>
      {renderItem(item, index, style)}
    </div>
  )
}

function VirtualizedListInner<T>(
  {
    items,
    height,
    itemSize,
    width = '100%',
    renderItem,
    className,
    overscanCount = 5,
    getKey,
    onScroll,
    initialScrollOffset = 0,
  }: VirtualizedListProps<T>,
  ref: React.ForwardedRef<List<ItemData<T>>>
) {
  const itemData = useMemo<ItemData<T>>(
    () => ({
      items,
      renderItem,
      getKey,
    }),
    [items, renderItem, getKey]
  )

  const handleScroll = useCallback(
    ({ scrollOffset }: { scrollOffset: number }) => {
      onScroll?.(scrollOffset)
    },
    [onScroll]
  )

  if (items.length === 0) {
    return null
  }

  return (
    <List
      ref={ref}
      className={cn('scrollbar-thin scrollbar-thumb-gray-300 dark:scrollbar-thumb-gray-600', className)}
      height={height}
      width={width}
      itemCount={items.length}
      itemSize={itemSize}
      itemData={itemData}
      overscanCount={overscanCount}
      onScroll={handleScroll}
      initialScrollOffset={initialScrollOffset}
    >
      {Row as React.ComponentType<ListChildComponentProps<ItemData<T>>>}
    </List>
  )
}

// Use type assertion to preserve generic type parameter
export const VirtualizedList = forwardRef(VirtualizedListInner) as <T>(
  props: VirtualizedListProps<T> & { ref?: React.ForwardedRef<List<ItemData<T>>> }
) => React.ReactElement

/**
 * Hook to determine if virtualization should be used
 * Returns true if item count exceeds threshold
 */
export function useVirtualization(itemCount: number, threshold = 50): boolean {
  return itemCount >= threshold
}

/**
 * Utility to calculate list height based on container or viewport
 */
export function calculateListHeight(
  options: {
    maxHeight?: number
    itemCount: number
    itemSize: number
    minHeight?: number
  }
): number {
  const { maxHeight = 600, itemCount, itemSize, minHeight = 100 } = options
  const contentHeight = itemCount * itemSize
  return Math.max(minHeight, Math.min(maxHeight, contentHeight))
}
