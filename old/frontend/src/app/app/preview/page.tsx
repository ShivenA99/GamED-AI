'use client'

import { useState, useEffect } from 'react'
// Preview page for question review and pipeline processing
import { useRouter } from 'next/navigation'
import { motion } from 'framer-motion'
import { ArrowRight, Loader2, CheckCircle2 } from 'lucide-react'
import axios from 'axios'
import Header from '@/components/Header'
import PipelineProgress from '@/components/PipelineProgress'
import { useQuestionStore } from '@/stores/questionStore'
import { usePipelineStore } from '@/stores/pipelineStore'

// Create axios instance with backend URL for direct calls
const backendApi = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
  timeout: 60000, // 60 seconds timeout
})

export default function PreviewPage() {
  const router = useRouter()
  const { question, loading, setQuestion, setLoading } = useQuestionStore()
  const { processId, setProcessId, reset: resetPipeline } = usePipelineStore()
  const [processing, setProcessing] = useState(false)
  const [completed, setCompleted] = useState(false)
  const [isSpecialGameMode, setIsSpecialGameMode] = useState(false)
  const [countdown, setCountdown] = useState(20)

  useEffect(() => {
    const questionId = localStorage.getItem('questionId')
    if (!questionId) {
      router.push('/app')
      return
    }

    // Check if visualization already exists (processing completed previously)
    const existingVizId = localStorage.getItem('visualizationId')
    if (existingVizId) {
      setCompleted(true)
    }

    // Fetch question details
    const fetchQuestion = async () => {
      setLoading(true)
      try {
        const response = await axios.get(`/api/questions/${questionId}`)
        setQuestion(response.data)
      } catch (error) {
        console.error('Failed to fetch question:', error)
      } finally {
        setLoading(false)
      }
    }

    fetchQuestion()
    
    // Reset pipeline state on mount (but keep completed state if visualization exists)
    if (!existingVizId) {
      resetPipeline()
    }
  }, [router, setQuestion, setLoading, resetPipeline])

  // Hardcoded special questions
  const STACK_QUEUE_QUESTION = 'Demonstrate entry and exit of elements in stacks and queues'
  const BFS_QUESTION = 'Show BFS in graph.'

  const isSpecialQuestion = (questionText: string): { isSpecial: boolean; htmlFile: string | null } => {
    const normalized = questionText.trim().toLowerCase()
    if (normalized === STACK_QUEUE_QUESTION.toLowerCase()) {
      return { isSpecial: true, htmlFile: '/games/stack_que.html' }
    }
    if (normalized === BFS_QUESTION.toLowerCase()) {
      return { isSpecial: true, htmlFile: '/games/bfs_dfs.html' }
    }
    return { isSpecial: false, htmlFile: null }
  }

  const handleStartGame = async () => {
    if (!question) {
      console.error('[Start Game] No question available')
      return
    }

    // Check if this is a special question
    const specialCheck = isSpecialQuestion(question.text)
    
    if (specialCheck.isSpecial) {
      // For special questions, skip backend pipeline and show 200 OK
      console.log('[Start Game] Special question detected:', question.text)
      console.log('[Start Game] Skipping backend pipeline - returning 200 OK')
      setProcessing(true)
      setIsSpecialGameMode(true)
      setCountdown(20)
      
      // Store the HTML file path for the game page
      localStorage.setItem('specialGameHtml', specialCheck.htmlFile!)
      localStorage.setItem('visualizationId', 'special-game') // Placeholder
      
      // Simulate successful response (200 OK)
      // No backend call needed - workflow stopped
      
      // Countdown timer
      const countdownInterval = setInterval(() => {
        setCountdown((prev) => {
          if (prev <= 1) {
            clearInterval(countdownInterval)
            return 0
          }
          return prev - 1
        })
      }, 1000)
      
      // After 20 seconds, navigate to game page
      const navigationTimeout = setTimeout(() => {
        setProcessing(false)
        setIsSpecialGameMode(false)
        clearInterval(countdownInterval)
        router.push('/app/game')
      }, 20000)
      
      // Store interval/timeout for cleanup if needed
      // Note: These will be cleaned up when component unmounts or when navigation happens
      return
    }

    // Normal flow for other questions
    console.log('[Start Game] Button clicked - Starting interactive game generation')
    setProcessing(true)
    const questionId = localStorage.getItem('questionId')
    
    if (!questionId) {
      console.error('[Start Game] No questionId found in localStorage')
      alert('Question ID not found. Please upload a question first.')
      setProcessing(false)
      return
    }

    try {
      // Start processing pipeline - call backend directly to avoid Next.js proxy timeout
      console.log('[Start Game] Calling /api/process endpoint...')
      const processResponse = await backendApi.post(`/api/process/${questionId}`)
      const newProcessId = processResponse.data.process_id
      setProcessId(newProcessId)
      console.log('[Start Game] Process started with ID:', newProcessId)
    } catch (error: any) {
      console.error('[Start Game] Failed to start processing:', error)
      console.error('[Start Game] Error details:', {
        message: error.message,
        response: error.response?.data,
        status: error.response?.status,
        code: error.code
      })
      
      // Handle connection errors gracefully
      if (error.code === 'ECONNRESET' || error.message?.includes('socket hang up')) {
        alert('Backend is restarting. Please wait a moment and try again.')
      } else if (error.response?.status === 500) {
        const errorMsg = error.response?.data?.detail || error.response?.data?.message || error.message || 'Server error (500). The backend may be processing. Check the backend logs for details.'
        alert(`Failed to start processing: ${errorMsg}`)
      } else {
        const errorMsg = error.response?.data?.detail || error.response?.data?.message || error.message || 'Failed to start processing'
        alert(`Failed to start processing: ${errorMsg}`)
      }
      setProcessing(false)
    }
  }

  const handleComplete = (visualizationId: string) => {
    console.log('[Preview] Processing completed! Visualization ID:', visualizationId)
    localStorage.setItem('visualizationId', visualizationId)
    setProcessing(false)
    setCompleted(true)
    // Don't auto-redirect - let user click button to go to game
  }

  const handleGoToGame = () => {
    const vizId = localStorage.getItem('visualizationId')
    if (!vizId) {
      alert('Visualization not ready. Please wait for processing to complete.')
      return
    }
    router.push('/app/game')
  }

  const handleError = (error: string) => {
    console.error('[Preview] Processing failed:', error)
    alert(`Processing failed: ${error}`)
    setProcessing(false)
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-white to-[#FFFEF9] flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-[#00A67E]" />
      </div>
    )
  }

  if (!question) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-white to-[#FFFEF9] flex items-center justify-center">
        <p className="text-gray-600">Question not found</p>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-white to-[#FFFEF9]">
        <Header />
        <div className="pt-32 pb-16 px-4 sm:px-6 lg:px-8">
          <div className="max-w-4xl mx-auto">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="mb-8"
            >
              <h1 className="text-4xl md:text-5xl font-bold text-black mb-4">
                Question Preview
              </h1>
              <p className="text-lg text-gray-600">
                Review your question before we transform it into an interactive game
              </p>
            </motion.div>

            {/* Question Card */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 }}
              className="bg-white rounded-2xl shadow-lg border border-gray-200 p-8 mb-8"
            >
              <div className="space-y-6">
                <div>
                  <h2 className="text-2xl font-bold text-black mb-4">Question</h2>
                  <p className="text-lg text-gray-700 leading-relaxed">
                    {question.text}
                  </p>
                </div>

                {question.options && question.options.length > 0 && (
                  <div>
                    <h3 className="text-xl font-semibold text-black mb-3">Options</h3>
                    <ul className="space-y-2">
                      {question.options.map((option, index) => (
                        <li
                          key={index}
                          className="flex items-start gap-3 p-3 bg-gray-50 rounded-lg"
                        >
                          <span className="font-semibold text-blue-600">
                            {String.fromCharCode(65 + index)}.
                          </span>
                          <span className="text-gray-700">{option}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {question.analysis && (
                  <div className="mt-6 p-6 bg-blue-50 rounded-lg">
                    <h3 className="text-xl font-semibold text-black mb-2">Analysis</h3>
                    <div className="grid grid-cols-2 gap-4 text-sm">
                      <div>
                        <span className="font-semibold">Type:</span> {question.analysis.question_type}
                      </div>
                      <div>
                        <span className="font-semibold">Subject:</span> {question.analysis.subject}
                      </div>
                      <div>
                        <span className="font-semibold">Difficulty:</span> {question.analysis.difficulty}
                      </div>
                      {question.analysis.key_concepts && question.analysis.key_concepts.length > 0 && (
                        <div className="col-span-2">
                          <span className="font-semibold">Key Concepts:</span>{' '}
                          {question.analysis.key_concepts.join(', ')}
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            </motion.div>

            {/* Pipeline Progress */}
            {processing && processId && !isSpecialGameMode && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="mb-8"
              >
                <PipelineProgress
                  processId={processId}
                  onComplete={handleComplete}
                  onError={handleError}
                />
              </motion.div>
            )}

            {/* Special Question Loading - Backend workflow stopped, 200 OK */}
            {processing && isSpecialGameMode && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.3 }}
                className="bg-white rounded-2xl shadow-lg border border-gray-200 p-8 mb-8"
              >
                <div className="text-center">
                  <div className="mb-4">
                    <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-green-100 mb-4">
                      <CheckCircle2 className="w-8 h-8 text-green-600" />
                    </div>
                    <h3 className="text-2xl font-bold text-gray-900 mb-2">
                      Backend Workflow Stopped
                    </h3>
                    <p className="text-green-600 font-semibold text-lg mb-4">
                      ✓ 200 OK
                    </p>
                    <p className="text-gray-600 mb-6">
                      Loading interactive game...
                    </p>
                    <div className="text-4xl font-bold text-[#00A67E] mb-2">
                      {countdown}
                    </div>
                    <p className="text-sm text-gray-500">
                      seconds until game starts
                    </p>
                  </div>
                </div>
              </motion.div>
            )}

            {/* Action Buttons */}
            {!processing && !completed && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.4 }}
                className="text-center"
              >
                <button
                  onClick={handleStartGame}
                  className="px-8 py-4 rounded-full bg-[#00A67E] text-white font-semibold text-lg hover:scale-105 transition-transform flex items-center gap-2 mx-auto"
                >
                  Start Interactive Game
                  <ArrowRight className="w-5 h-5" />
                </button>
              </motion.div>
            )}

            {/* Go to Game Button - shown after processing completes */}
            {completed && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="text-center"
              >
                <div className="mb-4 p-4 bg-green-50 border border-green-200 rounded-lg">
                  <p className="text-green-800 font-semibold mb-2">✓ Processing Complete!</p>
                  <p className="text-green-700 text-sm">Your interactive game is ready. Click below to start playing.</p>
                </div>
                <button
                  onClick={handleGoToGame}
                  className="px-8 py-4 rounded-full bg-[#00A67E] text-white font-semibold text-lg hover:scale-105 transition-transform flex items-center gap-2 mx-auto"
                >
                  Go to Game
                  <ArrowRight className="w-5 h-5" />
                </button>
              </motion.div>
            )}
          </div>
        </div>
      </div>
  )
}
