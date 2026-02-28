'use client'

import React, { useState, useCallback, useEffect } from 'react'

/**
 * MemoryMatch - Card matching game interaction component
 *
 * Users match pairs of related items (terms to definitions, images to labels, etc.)
 * Classic memory game adapted for educational content.
 */

export interface MatchPair {
  id: string
  front: string // First card content (term/image)
  back: string  // Second card content (definition/label)
  frontType: 'text' | 'image'
  backType: 'text' | 'image'
  explanation?: string // Educational note shown on match
  category?: string
}

export interface MemoryMatchProps {
  pairs: MatchPair[]
  gridSize?: [number, number] // [cols, rows]
  flipDurationMs?: number
  mismatchFlipMultiplier?: number
  showAttemptsCounter?: boolean
  onComplete: (result: MemoryMatchResult) => void
  instructions?: string
  showExplanationOnMatch?: boolean  // Fix 6.3: show explanation popup on match
  // Store integration props (Fix 1.7h) — optional for standalone use
  storeProgress?: { matchedPairIds: string[]; attempts: number; totalPairs: number } | null
  onPairMatched?: (pairId: string) => void
  onAttemptMade?: () => void
}

export interface MemoryMatchResult {
  isComplete: boolean
  score: number
  maxScore: number
  attempts: number
  perfectAttempts: number // Number of pairs to get perfect score
  matchedPairs: number
  totalPairs: number
}

interface Card {
  id: string
  pairId: string
  content: string
  contentType: 'text' | 'image'
  isFlipped: boolean
  isMatched: boolean
}

export function MemoryMatch({
  pairs,
  gridSize,
  flipDurationMs = 600,
  mismatchFlipMultiplier = 1.5,
  showAttemptsCounter = true,
  onComplete,
  instructions = 'Click cards to find matching pairs.',
  showExplanationOnMatch = false,
  storeProgress,
  onPairMatched,
  onAttemptMade,
}: MemoryMatchProps) {
  // Create cards from pairs (2 cards per pair)
  const [cards, setCards] = useState<Card[]>(() => {
    const allCards: Card[] = []
    pairs.forEach((pair) => {
      allCards.push({
        id: `${pair.id}-front`,
        pairId: pair.id,
        content: pair.front,
        contentType: pair.frontType,
        isFlipped: false,
        isMatched: false,
      })
      allCards.push({
        id: `${pair.id}-back`,
        pairId: pair.id,
        content: pair.back,
        contentType: pair.backType,
        isFlipped: false,
        isMatched: false,
      })
    })
    // Shuffle cards
    return allCards.sort(() => Math.random() - 0.5)
  })

  const [flippedCards, setFlippedCards] = useState<string[]>([])
  const [attempts, setAttempts] = useState(0)
  const [isChecking, setIsChecking] = useState(false)
  const [matchedCount, setMatchedCount] = useState(0)
  const [explanationPopup, setExplanationPopup] = useState<{ text: string; term: string } | null>(null)

  // Calculate grid dimensions
  const totalCards = cards.length
  const cols = gridSize?.[0] || Math.ceil(Math.sqrt(totalCards))
  const rows = gridSize?.[1] || Math.ceil(totalCards / cols)

  // Check for matches when two cards are flipped
  useEffect(() => {
    if (flippedCards.length === 2) {
      setIsChecking(true)
      setAttempts((prev) => prev + 1)
      onAttemptMade?.()

      const [first, second] = flippedCards
      const firstCard = cards.find((c) => c.id === first)
      const secondCard = cards.find((c) => c.id === second)

      if (firstCard && secondCard && firstCard.pairId === secondCard.pairId) {
        // Match found!
        onPairMatched?.(firstCard.pairId)
        // Fix 6.3: Show explanation popup on match
        if (showExplanationOnMatch) {
          const matchedPair = pairs.find(p => p.id === firstCard.pairId)
          if (matchedPair?.explanation) {
            setExplanationPopup({ text: matchedPair.explanation, term: matchedPair.front })
            setTimeout(() => setExplanationPopup(null), 3000)
          }
        }
        setTimeout(() => {
          setCards((prev) =>
            prev.map((c) =>
              c.pairId === firstCard.pairId ? { ...c, isMatched: true } : c
            )
          )
          setFlippedCards([])
          setMatchedCount((prev) => prev + 1)
          setIsChecking(false)
        }, flipDurationMs)
      } else {
        // No match - flip back
        setTimeout(() => {
          setCards((prev) =>
            prev.map((c) =>
              flippedCards.includes(c.id) ? { ...c, isFlipped: false } : c
            )
          )
          setFlippedCards([])
          setIsChecking(false)
        }, flipDurationMs * mismatchFlipMultiplier)
      }
    }
  }, [flippedCards, cards, flipDurationMs])

  // Check for game completion
  useEffect(() => {
    if (matchedCount === pairs.length && matchedCount > 0) {
      const perfectAttempts = pairs.length // Perfect = 1 attempt per pair
      const score = Math.max(
        0,
        Math.round(100 * (perfectAttempts / attempts))
      )

      onComplete({
        isComplete: true,
        score: Math.min(100, score),
        maxScore: 100,
        attempts,
        perfectAttempts,
        matchedPairs: matchedCount,
        totalPairs: pairs.length,
      })
    }
  }, [matchedCount, pairs.length, attempts, onComplete])

  const handleCardClick = useCallback(
    (cardId: string) => {
      if (isChecking) return

      const card = cards.find((c) => c.id === cardId)
      if (!card || card.isMatched || card.isFlipped) return

      if (flippedCards.length < 2) {
        setCards((prev) =>
          prev.map((c) => (c.id === cardId ? { ...c, isFlipped: true } : c))
        )
        setFlippedCards((prev) => [...prev, cardId])
      }
    },
    [cards, flippedCards, isChecking]
  )

  const handleReset = useCallback(() => {
    const allCards: Card[] = []
    pairs.forEach((pair) => {
      allCards.push({
        id: `${pair.id}-front`,
        pairId: pair.id,
        content: pair.front,
        contentType: pair.frontType,
        isFlipped: false,
        isMatched: false,
      })
      allCards.push({
        id: `${pair.id}-back`,
        pairId: pair.id,
        content: pair.back,
        contentType: pair.backType,
        isFlipped: false,
        isMatched: false,
      })
    })
    setCards(allCards.sort(() => Math.random() - 0.5))
    setFlippedCards([])
    setAttempts(0)
    setMatchedCount(0)
    setIsChecking(false)
  }, [pairs])

  return (
    <div className="w-full max-w-4xl mx-auto p-4">
      {/* Instructions */}
      <div className="mb-4 p-3 bg-blue-50 rounded-lg">
        <p className="text-sm text-blue-800">{instructions}</p>
      </div>

      {/* Stats bar */}
      <div className="flex justify-between items-center mb-4">
        <div className="flex gap-4 text-sm">
          <span className="px-3 py-1 bg-green-100 text-green-800 rounded-full">
            Matched: {matchedCount}/{pairs.length}
          </span>
          {showAttemptsCounter && (
            <span className="px-3 py-1 bg-blue-100 text-blue-800 rounded-full">
              Attempts: {attempts}
            </span>
          )}
        </div>
        <button
          onClick={handleReset}
          className="text-sm text-gray-500 hover:text-gray-700"
        >
          Reset
        </button>
      </div>

      {/* Fix 6.3: Explanation popup on match */}
      {explanationPopup && (
        <div className="mb-3 p-3 bg-green-50 border border-green-200 rounded-lg animate-in fade-in duration-300">
          <p className="text-sm font-medium text-green-800">{explanationPopup.term}</p>
          <p className="text-sm text-green-700 mt-1">{explanationPopup.text}</p>
        </div>
      )}

      {/* Card grid */}
      <div
        className="grid gap-3 mb-4"
        style={{
          gridTemplateColumns: `repeat(${cols}, minmax(0, 1fr))`,
        }}
      >
        {cards.map((card) => (
          <div
            key={card.id}
            onClick={() => handleCardClick(card.id)}
            className={`
              aspect-[4/3] relative cursor-pointer
              transition-all duration-300 transform
              ${card.isFlipped || card.isMatched ? '[transform:rotateY(180deg)]' : ''}
              ${card.isMatched ? 'opacity-60' : ''}
            `}
            style={{
              perspective: '1000px',
              transformStyle: 'preserve-3d',
            }}
          >
            {/* Card back (face down) */}
            <div
              className={`
                absolute inset-0 rounded-lg border-2 flex items-center justify-center
                transition-all duration-300
                ${card.isFlipped || card.isMatched
                  ? 'opacity-0 pointer-events-none'
                  : 'bg-gradient-to-br from-blue-500 to-purple-600 border-blue-600'
                }
              `}
            >
              <span className="text-white text-3xl">?</span>
            </div>

            {/* Card front (face up) */}
            <div
              className={`
                absolute inset-0 rounded-lg border-2 flex items-center justify-center p-2
                transition-all duration-300
                ${card.isFlipped || card.isMatched
                  ? 'bg-white border-gray-300'
                  : 'opacity-0 pointer-events-none'
                }
                ${card.isMatched ? 'border-green-400 bg-green-50' : ''}
              `}
            >
              {card.contentType === 'image' ? (
                <img
                  src={card.content}
                  alt="Card"
                  className="max-w-full max-h-full object-contain"
                />
              ) : (
                <p className="text-sm text-center text-gray-800 font-medium">
                  {card.content}
                </p>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Completion message */}
      {matchedCount === pairs.length && (
        <div className="p-4 bg-green-100 border border-green-300 rounded-lg text-center">
          <p className="text-lg font-bold text-green-800 mb-1">
            Congratulations! All pairs matched!
          </p>
          <p className="text-sm text-green-700">
            Completed in {attempts} attempts (perfect: {pairs.length})
          </p>
        </div>
      )}
    </div>
  )
}

export default MemoryMatch
