'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { motion } from 'framer-motion'
import { CheckCircle2, XCircle, Loader2 } from 'lucide-react'
import axios from 'axios'
import Header from '@/components/Header'
import { GameEngine } from '@/components/GameEngine'
import { SpecialGameViewer } from '@/components/SpecialGameViewer'
import type { GameBlueprint } from '@/types/gameBlueprint'

interface GameState {
  currentQuestion: number
  totalQuestions: number
  score: number
  answers: Array<{
    questionNumber: number
    selectedAnswer: string
    isCorrect: boolean
  }>
}

export default function GamePage() {
  const router = useRouter()
  const [blueprint, setBlueprint] = useState<GameBlueprint | null>(null)
  const [visualizationHtml, setVisualizationHtml] = useState<string>('')
  const [visualizationType, setVisualizationType] = useState<'blueprint' | 'html'>('html')
  const [loading, setLoading] = useState(true)
  const [gameState, setGameState] = useState<GameState>({
    currentQuestion: 0,
    totalQuestions: 0,
    score: 0,
    answers: [],
  })
  const [selectedAnswer, setSelectedAnswer] = useState<string | null>(null)
  const [showFeedback, setShowFeedback] = useState(false)
  const [isCorrect, setIsCorrect] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [specialGameHtml, setSpecialGameHtml] = useState<string | null>(null)

  useEffect(() => {
    // Check if this is a special game (HTML file stored in localStorage)
    const specialGameHtmlFile = localStorage.getItem('specialGameHtml')
    
    if (specialGameHtmlFile) {
      // Load the HTML file directly
      axios.get(specialGameHtmlFile, { responseType: 'text' })
        .then(response => {
          // Store the full HTML content (with CSS)
          setSpecialGameHtml(response.data)
          setLoading(false)
          // Clean up localStorage
          localStorage.removeItem('specialGameHtml')
        })
        .catch(error => {
          console.error('Failed to load special game HTML:', error)
          setError('Failed to load game')
          setLoading(false)
          localStorage.removeItem('specialGameHtml')
        })
      return
    }

    // Normal flow - check for visualization ID
    const visualizationId = localStorage.getItem('visualizationId')
    if (!visualizationId) {
      router.push('/app')
      return
    }

    const fetchVisualization = async () => {
      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
        const response = await axios.get(`${apiUrl}/api/visualization/${visualizationId}`)
        
        console.log('[Game] Visualization response:', {
          type: response.data.type,
          hasBlueprint: !!response.data.blueprint,
          hasHtml: !!response.data.html,
          hasQuestionData: !!response.data.question_data
        })
        
        if (response.data.type === 'blueprint' && response.data.blueprint) {
          // New blueprint-based visualization
          const blueprintJson = response.data.blueprint.blueprint
          if (blueprintJson && typeof blueprintJson === 'object') {
            setBlueprint(blueprintJson as GameBlueprint)
            setVisualizationType('blueprint')
            console.log('[Game] Blueprint loaded successfully')
          } else {
            console.error('[Game] Blueprint JSON is invalid:', blueprintJson)
            throw new Error('Blueprint data is missing or invalid in response')
          }
        } else if (response.data.html) {
          // Legacy HTML visualization
          setVisualizationHtml(response.data.html)
          setVisualizationType('html')
          
          // Extract question data from the visualization
          const questionData = response.data.question_data
          setGameState({
            currentQuestion: 0,
            totalQuestions: questionData?.question_flow?.length || 1,
            score: 0,
            answers: [],
          })
          console.log('[Game] HTML visualization loaded successfully')
        } else {
          throw new Error('Visualization response does not contain blueprint or HTML data')
        }
      } catch (error: any) {
        console.error('[Game] Failed to fetch visualization:', error)
        const errorMessage = error.response?.data?.detail || error.message || 'Failed to load visualization'
        setError(errorMessage)
        console.error('[Game] Error details:', {
          status: error.response?.status,
          data: error.response?.data,
          message: error.message
        })
      } finally {
        setLoading(false)
      }
    }

    fetchVisualization()
  }, [router])

  const handleAnswerSelect = (answer: string) => {
    setSelectedAnswer(answer)
  }

  const handleSubmitAnswer = async () => {
    if (!selectedAnswer) return

    // Get correct answer from visualization data
    const visualizationId = localStorage.getItem('visualizationId')
    try {
      const response = await axios.post(`/api/check-answer/${visualizationId}`, {
        questionNumber: gameState.currentQuestion + 1,
        selectedAnswer,
      })

      const correct = response.data.is_correct
      setIsCorrect(correct)

      const newScore = correct ? gameState.score + 1 : gameState.score
      const newAnswers = [
        ...gameState.answers,
        {
          questionNumber: gameState.currentQuestion + 1,
          selectedAnswer,
          isCorrect: correct,
        },
      ]

      setGameState({
        ...gameState,
        score: newScore,
        answers: newAnswers,
      })

      setShowFeedback(true)

      // Auto-advance after 2 seconds
      setTimeout(() => {
        if (gameState.currentQuestion + 1 < gameState.totalQuestions) {
          setGameState({
            ...gameState,
            currentQuestion: gameState.currentQuestion + 1,
            score: newScore,
            answers: newAnswers,
          })
          setSelectedAnswer(null)
          setShowFeedback(false)
        } else {
          // Game complete, navigate to score page
          localStorage.setItem('finalScore', newScore.toString())
          localStorage.setItem('totalQuestions', gameState.totalQuestions.toString())
          router.push('/app/score')
        }
      }, 2000)
    } catch (error) {
      console.error('Failed to check answer:', error)
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-white to-[#FFFEF9] flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-brilliant-green" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-white to-[#FFFEF9] flex items-center justify-center p-4">
        <div className="max-w-md w-full bg-white rounded-lg shadow-lg p-6">
          <div className="flex items-center gap-3 mb-4">
            <XCircle className="w-6 h-6 text-red-500" />
            <h2 className="text-xl font-semibold text-gray-900">Failed to Load Visualization</h2>
          </div>
          <p className="text-gray-600 mb-4">{error}</p>
          <button
            onClick={() => router.push('/app')}
            className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-[#00A67E] text-white rounded-lg hover:bg-[#008F6B] transition-colors"
          >
            Go Back
          </button>
        </div>
      </div>
    )
  }

  // If special game HTML is loaded, show it in immersive mode
  if (specialGameHtml) {
    return (
      <SpecialGameViewer
        htmlContent={specialGameHtml}
        onComplete={() => {
          // This will be handled by the SpecialGameViewer component
        }}
      />
    )
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-white to-[#FFFEF9]">
      <Header />
      <div className="pt-24 pb-16 px-4 sm:px-6 lg:px-8">
        <div className="max-w-6xl mx-auto">
          {/* Progress Bar */}
          <div className="mb-8">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-semibold text-black">
                Question {gameState.currentQuestion + 1} of {gameState.totalQuestions}
              </span>
              <span className="text-sm font-semibold text-brilliant-green">
                Score: {gameState.score}/{gameState.totalQuestions}
              </span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2">
              <motion.div
                className="bg-brilliant-green h-2 rounded-full"
                initial={{ width: 0 }}
                animate={{
                  width: `${((gameState.currentQuestion + 1) / gameState.totalQuestions) * 100}%`,
                }}
                transition={{ duration: 0.5 }}
              />
            </div>
          </div>

          {/* Visualization Container */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="bg-white rounded-2xl shadow-lg border border-gray-200 p-8 mb-8"
          >
            {visualizationType === 'blueprint' && blueprint ? (
              <GameEngine blueprint={blueprint} />
            ) : (
              <div
                className="visualization-container w-full"
                dangerouslySetInnerHTML={{ __html: visualizationHtml }}
              />
            )}
          </motion.div>

          {/* Feedback */}
          {showFeedback && (
            <motion.div
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              className={`mb-8 p-6 rounded-2xl ${
                isCorrect ? 'bg-mint-green' : 'bg-red-50'
              } flex items-center gap-4`}
            >
              {isCorrect ? (
                <CheckCircle2 className="w-8 h-8 text-brilliant-green" />
              ) : (
                <XCircle className="w-8 h-8 text-red-500" />
              )}
              <div>
                <p className={`font-semibold text-lg ${isCorrect ? 'text-brilliant-green' : 'text-red-700'}`}>
                  {isCorrect ? 'Correct!' : 'Incorrect'}
                </p>
                <p className={`text-sm ${isCorrect ? 'text-green-700' : 'text-red-600'}`}>
                  {isCorrect
                    ? 'Great job! Moving to next question...'
                    : "Don't worry, let's continue..."}
                </p>
              </div>
            </motion.div>
          )}
        </div>
      </div>
    </div>
  )
}

