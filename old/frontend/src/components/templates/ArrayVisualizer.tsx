'use client'

import { motion, AnimatePresence } from 'framer-motion'
import { useState, useEffect } from 'react'

interface ArrayElement {
  value: number
  index: number
  isActive?: boolean
  isLeft?: boolean
  isRight?: boolean
  isMid?: boolean
  isTarget?: boolean
  isSorted?: boolean
  isUnsorted?: boolean
  isFound?: boolean
  highlight?: 'compare' | 'decision' | 'found' | 'none'
}

interface ArrayVisualizerProps {
  array: number[]
  left?: number
  right?: number
  mid?: number
  target?: number
  highlightIndices?: number[]
  sortedRanges?: Array<{ start: number; end: number }>
  showIndices?: boolean
  onElementClick?: (index: number) => void
}

export function ArrayVisualizer({
  array,
  left,
  right,
  mid,
  target,
  highlightIndices = [],
  sortedRanges = [],
  showIndices = true,
  onElementClick
}: ArrayVisualizerProps) {
  const [elements, setElements] = useState<ArrayElement[]>([])

  useEffect(() => {
    const newElements: ArrayElement[] = array.map((value, index) => {
      const isInSortedRange = sortedRanges.some(
        range => index >= range.start && index <= range.end
      )

      return {
        value,
        index,
        isLeft: left !== undefined && index === left,
        isRight: right !== undefined && index === right,
        isMid: mid !== undefined && index === mid,
        isTarget: target !== undefined && value === target,
        isSorted: isInSortedRange,
        isUnsorted: !isInSortedRange && sortedRanges.length > 0,
        isFound: target !== undefined && value === target && mid === index,
        highlight: highlightIndices.includes(index) ? 'compare' : 'none'
      }
    })
    setElements(newElements)
  }, [array, left, right, mid, target, highlightIndices, sortedRanges])

  const getElementColor = (element: ArrayElement): string => {
    if (element.isFound) return 'bg-green-500 text-white'
    if (element.isMid) return 'bg-blue-500 text-white'
    if (element.isLeft || element.isRight) return 'bg-yellow-400 text-black'
    if (element.isTarget && element.highlight === 'compare') return 'bg-purple-400 text-white'
    if (element.highlight === 'compare') return 'bg-orange-400 text-white'
    if (element.isSorted) return 'bg-green-100 border-green-300'
    if (element.isUnsorted) return 'bg-red-100 border-red-300'
    return 'bg-gray-100 border-gray-300'
  }

  const getElementLabel = (element: ArrayElement): string => {
    const labels: string[] = []
    if (element.isLeft) labels.push('L')
    if (element.isRight) labels.push('R')
    if (element.isMid) labels.push('M')
    if (element.isTarget) labels.push('T')
    return labels.join(', ')
  }

  return (
    <div className="w-full">
      <div className="flex flex-wrap gap-2 justify-center items-end p-6 bg-gray-50 rounded-lg">
        <AnimatePresence mode="popLayout">
          {elements.map((element, idx) => (
            <motion.div
              key={`${element.index}-${element.value}`}
              initial={{ opacity: 0, y: -20 }}
              animate={{ 
                opacity: 1, 
                y: 0,
                scale: element.isMid || element.isFound ? 1.15 : 1,
                backgroundColor: getElementColor(element).includes('bg-') 
                  ? undefined 
                  : getElementColor(element)
              }}
              exit={{ opacity: 0, scale: 0.8 }}
              transition={{ 
                duration: 0.3,
                type: "spring",
                stiffness: 300
              }}
              whileHover={{ scale: 1.1 }}
              onClick={() => onElementClick?.(element.index)}
              className={`
                relative flex flex-col items-center justify-center
                w-16 h-16 rounded-lg border-2 font-bold text-lg
                cursor-pointer transition-all duration-200
                ${getElementColor(element)}
                ${element.isMid || element.isFound ? 'shadow-lg ring-2 ring-blue-500' : ''}
              `}
            >
              <motion.div
                animate={{ 
                  scale: element.highlight === 'compare' ? [1, 1.2, 1] : 1 
                }}
                transition={{ 
                  duration: 0.5,
                  repeat: element.highlight === 'compare' ? Infinity : 0
                }}
                className="text-center"
              >
                {element.value}
              </motion.div>
              
              {showIndices && (
                <div className="absolute -bottom-6 text-xs text-gray-600 font-normal">
                  {element.index}
                </div>
              )}
              
              {(element.isLeft || element.isRight || element.isMid || element.isTarget) && (
                <motion.div
                  initial={{ opacity: 0, y: -10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="absolute -top-6 text-xs font-semibold text-gray-700"
                >
                  {getElementLabel(element)}
                </motion.div>
              )}
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
      
      {/* Legend */}
      <div className="flex flex-wrap gap-4 mt-4 text-xs text-gray-600 justify-center">
        {left !== undefined && (
          <div className="flex items-center gap-1">
            <div className="w-4 h-4 bg-yellow-400 rounded"></div>
            <span>L (Left)</span>
          </div>
        )}
        {right !== undefined && (
          <div className="flex items-center gap-1">
            <div className="w-4 h-4 bg-yellow-400 rounded"></div>
            <span>R (Right)</span>
          </div>
        )}
        {mid !== undefined && (
          <div className="flex items-center gap-1">
            <div className="w-4 h-4 bg-blue-500 rounded"></div>
            <span>M (Mid)</span>
          </div>
        )}
        {target !== undefined && (
          <div className="flex items-center gap-1">
            <div className="w-4 h-4 bg-purple-400 rounded"></div>
            <span>T (Target)</span>
          </div>
        )}
        {sortedRanges.length > 0 && (
          <>
            <div className="flex items-center gap-1">
              <div className="w-4 h-4 bg-green-100 border border-green-300 rounded"></div>
              <span>Sorted</span>
            </div>
            <div className="flex items-center gap-1">
              <div className="w-4 h-4 bg-red-100 border border-red-300 rounded"></div>
              <span>Unsorted</span>
            </div>
          </>
        )}
      </div>
    </div>
  )
}

