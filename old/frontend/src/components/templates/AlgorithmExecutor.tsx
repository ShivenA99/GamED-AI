'use client'

/**
 * Generalized Algorithm Execution Engine
 * Handles different algorithm types: binary search, sorting, graph traversal, etc.
 */

import { AlgorithmStep } from './AlgorithmStepper'

export interface AlgorithmConfig {
  type: 'binary_search' | 'binary_search_rotated' | 'sorting' | 'graph' | 'custom'
  array?: number[]
  target?: number
  customLogic?: string // For custom algorithms
}

export class AlgorithmExecutor {
  private config: AlgorithmConfig
  private steps: AlgorithmStep[] = []
  private currentStepIndex = 0

  constructor(config: AlgorithmConfig) {
    this.config = config
  }

  /**
   * Execute binary search in rotated sorted array
   */
  executeBinarySearchRotated(array: number[], target: number): AlgorithmStep[] {
    const steps: AlgorithmStep[] = []
    let left = 0
    let right = array.length - 1

    // Find pivot point (rotation point)
    const pivot = this.findPivot(array)
    steps.push({
      stepNumber: 0,
      explanation: `Initial state: Array has ${array.length} elements, target is ${target}`,
      variables: { left, right, target, array: [...array] },
      highlightIndices: []
    })

    let stepNum = 1

    while (left <= right) {
      const mid = Math.floor((left + right) / 2)
      const midValue = array[mid]

      // Determine which half is sorted
      const leftSorted = array[left] <= midValue
      const rightSorted = midValue <= array[right]

      // Determine sorted ranges
      const sortedRanges: Array<{ start: number; end: number }> = []
      if (leftSorted && left < mid) {
        sortedRanges.push({ start: left, end: mid })
      }
      if (rightSorted && mid < right) {
        sortedRanges.push({ start: mid + 1, end: right })
      }

      let comparison = `nums[${mid}] = ${midValue}`
      let decision = ''
      let explanation = ''

      if (midValue === target) {
        steps.push({
          stepNumber: stepNum++,
          left,
          right,
          mid,
          target,
          comparison: `${comparison} == ${target}`,
          decision: `Found! Return index ${mid}`,
          explanation: `Target found at index ${mid}`,
          variables: { left, right, mid, target, found: true },
          highlightIndices: [mid],
          sortedRanges
        })
        return steps
      }

      if (leftSorted) {
        // Left half is sorted
        if (array[left] <= target && target < midValue) {
          // Target is in left half
          comparison += ` < ${target} && ${array[left]} <= ${target} < ${midValue}`
          decision = `Search left half [${left}, ${mid - 1}]`
          explanation = `Left half [${left}..${mid}] is sorted and contains target`
          right = mid - 1
        } else {
          // Target is in right half
          comparison += ` != ${target} && target not in sorted left half`
          decision = `Search right half [${mid + 1}, ${right}]`
          explanation = `Left half [${left}..${mid}] is sorted but doesn't contain target`
          left = mid + 1
        }
      } else {
        // Right half is sorted
        if (midValue < target && target <= array[right]) {
          // Target is in right half
          comparison += ` < ${target} && ${midValue} < ${target} <= ${array[right]}`
          decision = `Search right half [${mid + 1}, ${right}]`
          explanation = `Right half [${mid + 1}..${right}] is sorted and contains target`
          left = mid + 1
        } else {
          // Target is in left half
          comparison += ` != ${target} && target not in sorted right half`
          decision = `Search left half [${left}, ${mid - 1}]`
          explanation = `Right half [${mid + 1}..${right}] is sorted but doesn't contain target`
          right = mid - 1
        }
      }

      steps.push({
        stepNumber: stepNum++,
        left,
        right,
        mid,
        target,
        comparison,
        decision,
        explanation,
        variables: { left, right, mid, target, midValue },
        highlightIndices: [left, mid, right],
        sortedRanges
      })
    }

    // Not found
    steps.push({
      stepNumber: stepNum++,
      left,
      right,
      comparison: `left (${left}) > right (${right})`,
      decision: 'Target not found, return -1',
      explanation: 'Search space exhausted, target not in array',
      variables: { left, right, target, found: false },
      highlightIndices: []
    })

    return steps
  }

  /**
   * Execute standard binary search
   */
  executeBinarySearch(array: number[], target: number): AlgorithmStep[] {
    const steps: AlgorithmStep[] = []
    let left = 0
    let right = array.length - 1

    steps.push({
      stepNumber: 0,
      explanation: `Binary search: Looking for ${target} in sorted array`,
      variables: { left, right, target, array: [...array] },
      highlightIndices: []
    })

    let stepNum = 1

    while (left <= right) {
      const mid = Math.floor((left + right) / 2)
      const midValue = array[mid]

      const comparison = `nums[${mid}] = ${midValue}`
      let decision = ''
      let explanation = ''

      if (midValue === target) {
        steps.push({
          stepNumber: stepNum++,
          left,
          right,
          mid,
          target,
          comparison: `${comparison} == ${target}`,
          decision: `Found! Return index ${mid}`,
          explanation: `Target found at index ${mid}`,
          variables: { left, right, mid, target, found: true },
          highlightIndices: [mid],
          sortedRanges: [{ start: left, end: right }]
        })
        return steps
      } else if (midValue < target) {
        decision = `Search right half [${mid + 1}, ${right}]`
        explanation = `${midValue} < ${target}, so target must be in right half`
        left = mid + 1
      } else {
        decision = `Search left half [${left}, ${mid - 1}]`
        explanation = `${midValue} > ${target}, so target must be in left half`
        right = mid - 1
      }

      steps.push({
        stepNumber: stepNum++,
        left,
        right,
        mid,
        target,
        comparison: `${comparison} ${midValue < target ? '<' : '>'} ${target}`,
        decision,
        explanation,
        variables: { left, right, mid, target, midValue },
        highlightIndices: [left, mid, right],
        sortedRanges: [{ start: left, end: right }]
      })
    }

    steps.push({
      stepNumber: stepNum++,
      left,
      right,
      comparison: `left (${left}) > right (${right})`,
      decision: 'Target not found, return -1',
      explanation: 'Search space exhausted',
      variables: { left, right, target, found: false },
      highlightIndices: []
    })

    return steps
  }

  /**
   * Find pivot point in rotated array
   */
  private findPivot(array: number[]): number {
    let left = 0
    let right = array.length - 1

    while (left < right) {
      const mid = Math.floor((left + right) / 2)
      if (array[mid] > array[right]) {
        left = mid + 1
      } else {
        right = mid
      }
    }
    return left
  }

  /**
   * Execute algorithm based on config
   */
  execute(): AlgorithmStep[] {
    if (!this.config.array) {
      return [{
        stepNumber: 0,
        explanation: 'No array provided',
        variables: {}
      }]
    }

    switch (this.config.type) {
      case 'binary_search_rotated':
        return this.executeBinarySearchRotated(
          this.config.array,
          this.config.target ?? 0
        )
      case 'binary_search':
        return this.executeBinarySearch(
          this.config.array,
          this.config.target ?? 0
        )
      default:
        return [{
          stepNumber: 0,
          explanation: `Algorithm type ${this.config.type} not yet implemented`,
          variables: { type: this.config.type }
        }]
    }
  }
}

