'use client'

import { useState, useEffect, useMemo } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { CheckCircle2, XCircle, Send, AlertCircle, Home, RotateCcw, Trophy } from 'lucide-react'
import axios from 'axios'
import { useRouter } from 'next/navigation'
import type { ParameterPlaygroundBlueprint } from '@/types/gameBlueprint'
import { ArrayVisualizer } from './ArrayVisualizer'
import { AlgorithmStepper, AlgorithmStep } from './AlgorithmStepper'
import { StatePanel } from './StatePanel'
import { AlgorithmExecutor, AlgorithmConfig } from './AlgorithmExecutor'
import { TreeVisualizer } from './TreeVisualizer'

export function ParameterPlaygroundGame({ blueprint }: { blueprint: ParameterPlaygroundBlueprint }) {
  const router = useRouter()
  
  // Extract parameters
  const [parameters, setParameters] = useState<Record<string, any>>({})
  const [currentStep, setCurrentStep] = useState<AlgorithmStep | null>(null)
  const [algorithmSteps, setAlgorithmSteps] = useState<AlgorithmStep[]>([])
  
  // Task/Question state - for questions that must be answered before visualization
  const [currentTaskIndex, setCurrentTaskIndex] = useState(0)
  const [taskAnswers, setTaskAnswers] = useState<Record<string, string>>({})
  const [taskResults, setTaskResults] = useState<Record<string, { isCorrect: boolean; feedback?: string }>>({})
  const [showVisualization, setShowVisualization] = useState(false)
  const [isCompleted, setIsCompleted] = useState(false) // Track if question is completed
  
  // Tree traversal animation state
  const [activeTraversalType, setActiveTraversalType] = useState<'inorder' | 'preorder' | 'postorder' | 'level_order' | null>(null)
  const [traversalAnimationSpeed, setTraversalAnimationSpeed] = useState(500)
  
  // Answer state (for post-visualization questions)
  const [studentAnswer, setStudentAnswer] = useState<string>('')
  const [isChecking, setIsChecking] = useState(false)
  const [answerResult, setAnswerResult] = useState<{
    isCorrect: boolean
    correctAnswer: string | number
    feedback?: string
  } | null>(null)
  const [showAnswer, setShowAnswer] = useState(false)
  
  // Get current task (first required task)
  const currentTask = blueprint.tasks?.find((task, idx) => 
    task.requiredToProceed && idx >= currentTaskIndex
  ) || blueprint.tasks?.[0]
  
  // Check if current task is answered
  const isCurrentTaskAnswered = currentTask ? taskAnswers[currentTask.id] !== undefined : true
  
  // Show visualization if no required tasks or if all required tasks are answered
  const hasRequiredTasks = blueprint.tasks?.some(t => t.requiredToProceed) ?? false
  const shouldShowVisualization = !hasRequiredTasks || showVisualization

  // Initialize parameters from blueprint
  useEffect(() => {
    const initialParams: Record<string, any> = {}
    if (blueprint.parameters && Array.isArray(blueprint.parameters)) {
      blueprint.parameters.forEach(param => {
        initialParams[param.id] = param.defaultValue
      })
    }
    setParameters(initialParams)
  }, [blueprint])

  // Determine algorithm type and execute
  useEffect(() => {
    const viz = blueprint.visualization
    if (!viz) {
      console.warn('[ParameterPlaygroundGame] No visualization object in blueprint')
      return
    }
    
    // Check if we have pre-computed steps
    if (viz.steps && viz.steps.length > 0) {
      setAlgorithmSteps(viz.steps)
      return
    }

    // Otherwise, execute algorithm based on type
    if (viz.algorithmType && viz.array) {
      const config: AlgorithmConfig = {
        type: viz.algorithmType,
        array: viz.array,
        target: viz.target
      }
      
      const executor = new AlgorithmExecutor(config)
      const steps = executor.execute()
      setAlgorithmSteps(steps)
    }
  }, [blueprint.visualization])

  // Get current array and target from parameters or blueprint
  const currentArray = useMemo(() => {
    // Try to get from parameters first
    const arrayParam = blueprint.parameters?.find(p => p.id === 'array' || p.id === 'nums')
    if (arrayParam && parameters[arrayParam.id]) {
      try {
        const value = parameters[arrayParam.id]
        if (typeof value === 'string') {
          // Parse array string like "[1,2,3]" or "1,2,3"
          const cleaned = value.trim().replace(/^\[|\]$/g, '')
          const parsed = cleaned.split(',').map(s => {
            const num = Number(s.trim())
            return isNaN(num) ? null : num
          }).filter(n => n !== null) as number[]
          return parsed.length > 0 ? parsed : []
        }
        return Array.isArray(value) ? value : []
      } catch {
        return []
      }
    }
    // Fallback to blueprint
    return blueprint.visualization?.array || []
  }, [parameters, blueprint])

  const currentTarget = useMemo(() => {
    const targetParam = blueprint.parameters?.find(p => p.id === 'target')
    if (targetParam && parameters[targetParam.id] !== undefined) {
      return Number(parameters[targetParam.id])
    }
    return blueprint.visualization?.target
  }, [parameters, blueprint])

  // Handle parameter changes
  const handleParameterChange = (paramId: string, value: any) => {
    setParameters(prev => ({ ...prev, [paramId]: value }))
    
    // Re-execute algorithm if array or target changed
    if (paramId === 'array' || paramId === 'nums' || paramId === 'target') {
      const viz = blueprint.visualization
      if (!viz || !viz.algorithmType) {
        return
      }
      
      // Parse array if it's a string
      let parsedArray = currentArray
      if (paramId === 'array' || paramId === 'nums') {
        if (typeof value === 'string') {
          const cleaned = value.trim().replace(/^\[|\]$/g, '')
          parsedArray = cleaned.split(',').map(s => {
            const num = Number(s.trim())
            return isNaN(num) ? null : num
          }).filter(n => n !== null) as number[]
        } else if (Array.isArray(value)) {
          parsedArray = value
        }
      }
      
      const config: AlgorithmConfig = {
        type: viz.algorithmType,
        array: parsedArray,
        target: paramId === 'target' ? Number(value) : currentTarget
      }
      
      const executor = new AlgorithmExecutor(config)
      const steps = executor.execute()
      setAlgorithmSteps(steps)
    }
  }

  // Calculate correct answer from algorithm execution
  const correctAnswer = useMemo(() => {
    if (algorithmSteps.length === 0) return null
    
    // Find the step that shows "Found! Return index"
    const foundStep = algorithmSteps.find(step => 
      step.decision?.includes('Found! Return index') ||
      step.decision?.includes('Found!') ||
      (step.variables?.found === true)
    )
    
    if (foundStep) {
      // Extract index from decision text like "Found! Return index 5"
      const match = foundStep.decision?.match(/Return index (\d+)/)
      if (match) {
        return parseInt(match[1])
      }
      // Fallback to mid value
      return foundStep.mid ?? foundStep.variables?.mid ?? -1
    }
    
    // Check final step for "not found" or "return -1"
    const finalStep = algorithmSteps[algorithmSteps.length - 1]
    if (finalStep.decision?.includes('not found') || 
        finalStep.decision?.includes('return -1') ||
        finalStep.decision?.includes('Target not found') ||
        finalStep.variables?.found === false) {
      return -1
    }
    
    return null
  }, [algorithmSteps])

  // Handle answer submission
  const handleCheckAnswer = async () => {
    if (!studentAnswer.trim()) {
      setAnswerResult({
        isCorrect: false,
        correctAnswer: correctAnswer ?? 'Unknown',
        feedback: 'Please enter an answer before checking.'
      })
      return
    }

    setIsChecking(true)
    setShowAnswer(false)

    try {
      // Parse student answer (handle both string and number)
      const studentAnswerNum = parseInt(studentAnswer.trim())
      const correctAnswerNum = correctAnswer !== null ? Number(correctAnswer) : null

      if (correctAnswerNum === null) {
        setAnswerResult({
          isCorrect: false,
          correctAnswer: 'Unknown',
          feedback: 'Unable to determine correct answer. Please ensure the algorithm has completed execution.'
        })
        setIsChecking(false)
        return
      }

      const isCorrect = studentAnswerNum === correctAnswerNum

      // Get feedback based on answer
      let feedback = ''
      if (isCorrect) {
        feedback = 'Excellent! You correctly identified the index. The algorithm found the target using binary search.'
      } else {
        if (correctAnswerNum === -1) {
          feedback = `The target is not in the array, so the algorithm returns -1. Your answer was ${studentAnswerNum}.`
        } else {
          feedback = `The correct answer is ${correctAnswerNum}. The algorithm found the target at index ${correctAnswerNum} using binary search.`
        }
      }

      setAnswerResult({
        isCorrect,
        correctAnswer: correctAnswerNum,
        feedback
      })
      setShowAnswer(true)

      // Also try to check via backend if visualization_id is available
      const visualizationId = localStorage.getItem('visualizationId')
      if (visualizationId) {
        try {
          await axios.post(`/api/check-answer/${visualizationId}`, {
            questionNumber: 1,
            selectedAnswer: studentAnswer.trim()
          })
        } catch (error) {
          // Backend check failed, but we already have local result
          console.warn('Backend answer check failed, using local result:', error)
        }
      }
    } catch (error) {
      console.error('Error checking answer:', error)
      setAnswerResult({
        isCorrect: false,
        correctAnswer: correctAnswer ?? 'Unknown',
        feedback: 'Error checking answer. Please try again.'
      })
    } finally {
      setIsChecking(false)
    }
  }

  // Reset answer when parameters change
  useEffect(() => {
    setStudentAnswer('')
    setAnswerResult(null)
    setShowAnswer(false)
  }, [parameters, currentArray, currentTarget])

  // Handle task answer submission - SIMPLIFIED VERSION
  const handleTaskSubmit = (taskId: string) => {
    const task = blueprint.tasks?.find(t => t.id === taskId)
    if (!task) return
    
    const selectedAnswer = taskAnswers[taskId]
    if (!selectedAnswer) return
    
    // Get correct answer - try multiple sources
    let correctAnswer = (task as any).correctAnswer
    
    // Simple comparison function
    const compareAnswers = (selected: any, correct: any): boolean => {
      // Convert both to strings and trim
      const s = String(selected).trim()
      const c = String(correct).trim()
      
      // Direct comparison
      if (s === c) return true
      
      // Number comparison (handle "3" vs 3)
      const sNum = Number(s)
      const cNum = Number(c)
      if (!isNaN(sNum) && !isNaN(cNum) && sNum === cNum) return true
      
      return false
    }
    
    // Check if answer is correct
    let isCorrect = false
    if (correctAnswer !== undefined && correctAnswer !== null) {
      isCorrect = compareAnswers(selectedAnswer, correctAnswer)
      console.log('Answer Check:', {
        selectedAnswer,
        correctAnswer,
        isCorrect,
        taskId
      })
    } else {
      // Fallback: if correctAnswer missing, check if it's in the first option (temporary)
      console.error('correctAnswer missing from task:', task)
      isCorrect = false // Default to incorrect if we can't verify
    }
    
    // Get feedback
    const feedback = isCorrect 
      ? ((task as any).correctFeedback || '✅ Correct!')
      : ((task as any).incorrectFeedback || '❌ Incorrect. Try again.')
    
    setTaskResults(prev => ({ ...prev, [taskId]: { isCorrect, feedback } }))
    
    // Update score via API (fire and forget)
    const visualizationId = localStorage.getItem('visualizationId')
    if (visualizationId) {
      axios.post(`/api/check-answer/${visualizationId}`, {
        questionNumber: currentTaskIndex + 1,
        selectedAnswer: selectedAnswer
      }).catch(error => {
        console.warn('Failed to update score:', error)
      })
    }
    
    // If correct and required to proceed, show visualization
    if (isCorrect && task.requiredToProceed) {
      setTimeout(() => {
        setShowVisualization(true)
        // User will click button to proceed to completion screen
      }, 1500)
    }
  }

  // Handle reset for "Attempt Again"
  const handleReset = () => {
    setIsCompleted(false)
    setShowVisualization(false)
    setTaskAnswers({})
    setTaskResults({})
    setCurrentTaskIndex(0)
    setCurrentStep(null)
    setAlgorithmSteps([])
    setStudentAnswer('')
    setAnswerResult(null)
    setShowAnswer(false)
  }

  return (
    <div id="gameRoot" className="flex flex-col gap-6 p-6 max-w-7xl mx-auto">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="space-y-2"
      >
        <h2 className="text-3xl font-bold text-gray-900">{blueprint.title}</h2>
        <p className="text-gray-600 text-lg">{blueprint.narrativeIntro}</p>
      </motion.div>

      {/* Question/Task Section - Display FIRST, before visualization */}
      {currentTask && !showVisualization && (
        <div className="space-y-6">
          {/* Question Card with Animations */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="bg-gradient-to-b from-white to-blue-50 rounded-2xl border-2 border-blue-400 shadow-xl p-8"
          >
            <motion.div
              initial={{ scale: 0.8, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              transition={{ delay: 0.2, type: "spring" }}
              className="flex items-center gap-3 mb-6"
            >
              <motion.div
                initial={{ rotate: -180 }}
                animate={{ rotate: 0 }}
                transition={{ delay: 0.3, type: "spring" }}
                className="bg-blue-600 text-white rounded-full w-10 h-10 flex items-center justify-center font-bold text-lg shadow-md"
              >
                {currentTaskIndex + 1}
              </motion.div>
              <h3 className="text-3xl font-bold text-black">Question</h3>
            </motion.div>
            
            <motion.p
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.4 }}
              className="text-xl text-gray-800 mb-8 font-medium leading-relaxed"
            >
              {currentTask.questionText}
            </motion.p>

            {/* Visual Preview - Show static visualization during question */}
            {blueprint.visualization && (() => {
              const viz = blueprint.visualization as any;
              return (
                <motion.div
                  initial={{ opacity: 0, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ delay: 0.5 }}
                  className="mb-8 bg-gradient-to-br from-purple-50 to-blue-50 rounded-xl p-6 border-2 border-blue-300 shadow-lg"
                >
                  <h4 className="text-sm font-semibold text-gray-700 mb-4 flex items-center gap-2">
                    <AlertCircle className="w-4 h-4 text-blue-600" />
                    Visual Preview
                  </h4>
                  
                  {/* Array visualization */}
                  {viz.array && viz.array.length > 0 && (
                    <div className="flex items-center justify-center gap-3 flex-wrap">
                      {viz.array.map((value: number, idx: number) => (
                        <motion.div
                          key={idx}
                          initial={{ scale: 0, rotate: -180 }}
                          animate={{ scale: 1, rotate: 0 }}
                          transition={{ delay: 0.6 + idx * 0.1, type: "spring", stiffness: 200 }}
                          className="w-16 h-16 bg-white rounded-xl border-2 border-blue-500 flex items-center justify-center shadow-md hover:scale-110 transition-transform"
                        >
                          <span className="text-2xl font-bold text-gray-900">{value}</span>
                        </motion.div>
                      ))}
                    </div>
                  )}
                  
                  {/* Matrix visualization */}
                  {viz.matrix && viz.matrix.length > 0 && (
                    <div className="flex flex-col items-center gap-2">
                      {viz.matrix.map((row: number[], rowIdx: number) => (
                        <div key={rowIdx} className="flex gap-2">
                          {row.map((value: number, colIdx: number) => (
                            <motion.div
                              key={colIdx}
                              initial={{ scale: 0 }}
                              animate={{ scale: 1 }}
                              transition={{ delay: 0.6 + (rowIdx * row.length + colIdx) * 0.05, type: "spring" }}
                              className="w-12 h-12 bg-white rounded-lg border-2 border-blue-500 flex items-center justify-center shadow-md"
                            >
                              <span className="text-lg font-bold text-gray-900">{value}</span>
                            </motion.div>
                          ))}
                        </div>
                      ))}
                    </div>
                  )}
                  
                  {/* Linked List visualization */}
                  {viz.linkedListNodes && viz.linkedListNodes.length > 0 && (
                    <div className="flex items-center justify-center gap-2 flex-wrap">
                      {viz.linkedListNodes.map((value: number, idx: number) => (
                        <div key={idx} className="flex items-center gap-1">
                          <motion.div
                            initial={{ scale: 0 }}
                            animate={{ scale: 1 }}
                            transition={{ delay: 0.6 + idx * 0.1, type: "spring" }}
                            className="w-14 h-14 bg-white rounded-lg border-2 border-blue-500 flex items-center justify-center shadow-md"
                          >
                            <span className="text-lg font-bold text-gray-900">{value}</span>
                          </motion.div>
                          {idx < viz.linkedListNodes.length - 1 && (
                            <motion.div
                              initial={{ scaleX: 0 }}
                              animate={{ scaleX: 1 }}
                              transition={{ delay: 0.7 + idx * 0.1 }}
                              className="w-8 h-0.5 bg-blue-500"
                            />
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                  
                  {/* Tree visualization with traversal animations */}
                  {viz.treeNodes && viz.treeNodes.length > 0 && (
                    <div className="w-full flex items-center justify-center">
                      <TreeVisualizer
                        treeNodes={viz.treeNodes}
                        traversalType={activeTraversalType}
                        animationSpeed={traversalAnimationSpeed}
                        showTree={true}
                        onTraversalComplete={() => {
                          // Animation completed
                        }}
                      />
                    </div>
                  )}
                  
                  {/* Asset image */}
                  {viz.assetUrl && (
                    <motion.div
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      transition={{ delay: 0.6 }}
                      className="mt-4"
                    >
                      <img 
                        src={viz.assetUrl} 
                        alt="Visualization preview" 
                        className="w-full rounded-lg shadow-md"
                      />
                    </motion.div>
                  )}
                </motion.div>
              );
            })()}

            {/* Answer Options - Multiple Choice */}
            {(currentTask as any).options && Array.isArray((currentTask as any).options) && (currentTask as any).options.length > 0 ? (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.7 }}
                className="space-y-3 mb-6"
              >
                {(currentTask as any).options.map((option: { 
                  value: string; 
                  label: string; 
                  traversalType?: 'inorder' | 'preorder' | 'postorder' | 'level_order';
                  animationSpeed?: number;
                }, idx: number) => (
                  <motion.button
                    key={idx}
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 0.8 + idx * 0.1 }}
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                    onClick={() => {
                      // Set the answer
                      setTaskAnswers(prev => ({ ...prev, [currentTask.id]: option.value }))
                      setTaskResults(prev => {
                        const { [currentTask.id]: _, ...rest } = prev
                        return rest
                      })
                      
                      // Trigger traversal animation if this is a tree traversal question
                      const viz = blueprint.visualization as any
                      if (viz?.treeNodes) {
                        // Extract traversal type from option if not explicitly set
                        let traversalType: 'inorder' | 'preorder' | 'postorder' | 'level_order' | undefined = option.traversalType
                        if (!traversalType) {
                          // Try to infer from label
                          const label = option.label.toLowerCase()
                          if (label.includes('inorder')) traversalType = 'inorder'
                          else if (label.includes('preorder')) traversalType = 'preorder'
                          else if (label.includes('postorder')) traversalType = 'postorder'
                          else if (label.includes('level order') || label.includes('level-order')) traversalType = 'level_order'
                        }
                        
                        if (traversalType) {
                          // Reset and trigger new traversal animation
                          const finalTraversalType: 'inorder' | 'preorder' | 'postorder' | 'level_order' = traversalType
                          setActiveTraversalType(null)
                          setTimeout(() => {
                            setActiveTraversalType(finalTraversalType)
                            if (option.animationSpeed) {
                              setTraversalAnimationSpeed(option.animationSpeed)
                            } else {
                              // Default speeds based on traversal type
                              const defaultSpeeds: Record<'inorder' | 'preorder' | 'postorder' | 'level_order', number> = {
                                'preorder': 300,
                                'inorder': 600,
                                'postorder': 900,
                                'level_order': 1200
                              }
                              setTraversalAnimationSpeed(defaultSpeeds[finalTraversalType] || 500)
                            }
                          }, 50)
                        }
                      }
                    }}
                    className={`w-full text-left p-5 rounded-xl border-2 transition-all ${
                      taskAnswers[currentTask.id] === option.value
                        ? 'border-blue-600 bg-blue-100 shadow-lg scale-[1.02]'
                        : 'border-gray-300 bg-white hover:border-blue-500 hover:bg-blue-50'
                    }`}
                  >
                    <div className="flex items-center gap-4">
                      <div className={`w-6 h-6 rounded-full border-2 flex items-center justify-center transition-all ${
                        taskAnswers[currentTask.id] === option.value
                          ? 'border-blue-600 bg-blue-600 shadow-md'
                          : 'border-gray-400'
                      }`}>
                        {taskAnswers[currentTask.id] === option.value && (
                          <motion.div
                            initial={{ scale: 0 }}
                            animate={{ scale: 1 }}
                            className="w-3 h-3 rounded-full bg-white"
                          />
                        )}
                      </div>
                      <span className="text-lg font-semibold text-black">{option.label}</span>
                    </div>
                  </motion.button>
                ))}
              </motion.div>
            ) : (
              /* Text Input for non-multiple-choice tasks */
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.7 }}
                className="mb-6"
              >
                <input
                  type="text"
                  value={taskAnswers[currentTask.id] || ''}
                  onChange={(e) => {
                    setTaskAnswers(prev => ({ ...prev, [currentTask.id]: e.target.value }))
                    setTaskResults(prev => {
                      const { [currentTask.id]: _, ...rest } = prev
                      return rest
                    })
                  }}
                  placeholder="Enter your answer..."
                  className="w-full px-5 py-4 border-2 border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-lg transition-all"
                />
              </motion.div>
            )}

            {/* Submit Button */}
            <motion.button
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 1.2 }}
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={() => handleTaskSubmit(currentTask.id)}
              disabled={!taskAnswers[currentTask.id]}
              className="w-full py-5 bg-blue-600 text-white rounded-xl font-bold text-lg hover:bg-blue-700 transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-lg disabled:shadow-none flex items-center justify-center gap-2"
            >
              <Send className="w-5 h-5" />
              Submit Answer
            </motion.button>

            {/* Feedback */}
            {taskResults[currentTask.id] && (
              <motion.div
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ type: "spring" }}
                className={`mt-6 p-6 rounded-xl border-2 ${
                  taskResults[currentTask.id].isCorrect
                    ? 'bg-green-100 border-green-500'
                    : 'bg-red-50 border-red-400'
                }`}
              >
                <div className="flex items-start gap-4">
                  {taskResults[currentTask.id].isCorrect ? (
                    <motion.div
                      initial={{ scale: 0, rotate: -180 }}
                      animate={{ scale: 1, rotate: 0 }}
                      transition={{ type: "spring", stiffness: 200 }}
                    >
                      <CheckCircle2 className="w-8 h-8 text-green-600 flex-shrink-0" />
                    </motion.div>
                  ) : (
                    <XCircle className="w-8 h-8 text-red-600 flex-shrink-0" />
                  )}
                  <div>
                    <p className={`font-bold text-xl mb-2 ${
                      taskResults[currentTask.id].isCorrect                       ? 'text-green-800' : 'text-red-800'
                    }`}>
                      {taskResults[currentTask.id].isCorrect ? '✅ Correct!' : '❌ Incorrect'}
                    </p>
                    <p className={`text-base ${
                      taskResults[currentTask.id].isCorrect ? 'text-green-700' : 'text-red-700'
                    }`}>
                      {taskResults[currentTask.id].feedback}
                    </p>
                  </div>
                </div>
              </motion.div>
            )}
          </motion.div>
        </div>
      )}

      {/* Visualization Section - Only show after answer submission (or if no required tasks) */}
      {shouldShowVisualization && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left Column: Parameters */}
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.1 }}
            className="space-y-4"
          >
          <h3 className="text-xl font-semibold text-gray-800">Parameters</h3>
          <div className="space-y-4 bg-white rounded-lg border border-gray-200 p-4">
            {blueprint.parameters && Array.isArray(blueprint.parameters) && blueprint.parameters.length > 0 ? (
              blueprint.parameters.map(param => (
                <div key={param.id}>
                  <label className="block mb-2 text-sm font-medium text-gray-700">
                    {param.label}
                    {param.unit && <span className="text-gray-500 ml-1">({param.unit})</span>}
                  </label>
                  {param.type === 'slider' && (
                    <div className="space-y-2">
                      <input
                        type="range"
                        min={param.min}
                        max={param.max}
                        value={parameters[param.id] || param.defaultValue}
                        onChange={(e) => handleParameterChange(param.id, Number(e.target.value))}
                        className="w-full"
                      />
                      <div className="text-sm text-gray-600 text-center">
                        {parameters[param.id] ?? param.defaultValue}
                      </div>
                    </div>
                  )}
                  {param.type === 'input' && (
                    <input
                      type="text"
                      value={parameters[param.id] ?? param.defaultValue}
                      onChange={(e) => handleParameterChange(param.id, e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#00A67E] focus:border-transparent"
                      placeholder={String(param.defaultValue)}
                    />
                  )}
                  {param.type === 'dropdown' && (
                    <select
                      value={parameters[param.id] ?? param.defaultValue}
                      onChange={(e) => handleParameterChange(param.id, e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#00A67E] focus:border-transparent"
                    >
                      {/* Add options if needed */}
                    </select>
                  )}
                </div>
              ))
            ) : (
              <p className="text-sm text-gray-500">No parameters available</p>
            )}
          </div>

          {/* State Panel */}
          {currentStep && (
            <StatePanel
              variables={currentStep.variables}
              code={blueprint.visualization?.code}
              explanation={currentStep.explanation}
            />
          )}
        </motion.div>

        {/* Middle Column: Visualization */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="lg:col-span-2 space-y-4"
        >
          <h3 className="text-xl font-semibold text-gray-800">Visualization</h3>
          
          {/* Array Visualization */}
          {blueprint.visualization?.algorithmType && currentArray.length > 0 ? (
            <div className="bg-white rounded-lg border border-gray-200 p-6">
              <ArrayVisualizer
                array={currentArray}
                left={currentStep?.left}
                right={currentStep?.right}
                mid={currentStep?.mid}
                target={currentTarget}
                highlightIndices={currentStep?.highlightIndices || []}
                sortedRanges={currentStep?.sortedRanges}
                showIndices={true}
              />
            </div>
          ) : blueprint.visualization?.assetUrl ? (
            <div className="bg-white rounded-lg border border-gray-200 p-4">
              <img 
                src={blueprint.visualization.assetUrl} 
                alt="Visualization" 
                className="w-full rounded-lg"
              />
            </div>
          ) : (
            <div className="bg-gray-50 rounded-lg border border-gray-200 p-12 text-center text-gray-500">
              No visualization available
            </div>
          )}

          {/* Algorithm Stepper */}
          {algorithmSteps.length > 0 && (
            <div className="bg-white rounded-lg border border-gray-200 p-6">
              <AlgorithmStepper
                steps={algorithmSteps}
                onStepChange={(step: AlgorithmStep) => setCurrentStep(step)}
                autoPlay={false}
                speed={1500}
              />
            </div>
          )}

          {/* Answer Input Section */}
          {algorithmSteps.length > 0 && correctAnswer !== null && Array.isArray(currentArray) && currentArray.length > 0 && currentTarget !== undefined && currentTarget !== null && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="bg-white rounded-lg border-2 border-[#00A67E] p-6 space-y-4"
            >
              <h3 className="text-xl font-semibold text-gray-800 flex items-center gap-2">
                <AlertCircle className="w-5 h-5 text-[#00A67E]" />
                Test Your Understanding
              </h3>
              
              <div className="space-y-4">
                <div>
                  <p className="text-gray-700 mb-3 font-medium">
                    Based on the algorithm execution above, what index will be returned for the target value?
                  </p>
                  <p className="text-sm text-gray-600 mb-4">
                    Array: <code className="bg-gray-100 px-2 py-1 rounded font-mono">
                      {Array.isArray(currentArray) && currentArray.length > 0 
                        ? `[${currentArray.join(', ')}]` 
                        : 'No array'}
                    </code>
                    {' '}Target: <code className="bg-gray-100 px-2 py-1 rounded font-mono">
                      {currentTarget !== undefined && currentTarget !== null 
                        ? currentTarget 
                        : 'No target'}
                    </code>
                  </p>
                </div>

                <div className="flex gap-3">
                  <input
                    type="text"
                    value={studentAnswer}
                    onChange={(e) => {
                      setStudentAnswer(e.target.value)
                      setAnswerResult(null)
                      setShowAnswer(false)
                    }}
                    placeholder="Enter index (e.g., 5 or -1)"
                    className="flex-1 px-4 py-3 border-2 border-gray-300 rounded-lg focus:ring-2 focus:ring-[#00A67E] focus:border-[#00A67E] text-lg font-mono"
                    disabled={isChecking}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' && !isChecking) {
                        e.preventDefault()
                        handleCheckAnswer()
                      }
                    }}
                  />
                  <button
                    onClick={handleCheckAnswer}
                    disabled={isChecking || !studentAnswer.trim()}
                    className="px-6 py-3 bg-[#00A67E] text-white rounded-lg hover:bg-[#008F6B] transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 font-semibold shadow-md"
                  >
                    {isChecking ? (
                      <>
                        <motion.div
                          animate={{ rotate: 360 }}
                          transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
                          className="w-5 h-5 border-2 border-white border-t-transparent rounded-full"
                        />
                        Checking...
                      </>
                    ) : (
                      <>
                        <Send className="w-5 h-5" />
                        Check Answer
                      </>
                    )}
                  </button>
                </div>

                {/* Answer Feedback */}
                <AnimatePresence>
                  {answerResult && showAnswer && (
                    <motion.div
                      initial={{ opacity: 0, y: -10 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0 }}
                      className={`p-4 rounded-lg border-2 ${
                        answerResult.isCorrect
                          ? 'bg-green-50 border-green-300'
                          : 'bg-red-50 border-red-300'
                      }`}
                    >
                      <div className="flex items-start gap-3">
                        {answerResult.isCorrect ? (
                          <CheckCircle2 className="w-6 h-6 text-green-600 flex-shrink-0 mt-0.5" />
                        ) : (
                          <XCircle className="w-6 h-6 text-red-600 flex-shrink-0 mt-0.5" />
                        )}
                        <div className="flex-1">
                          <h4 className={`font-semibold text-lg mb-2 ${
                            answerResult.isCorrect ? 'text-green-800' : 'text-red-800'
                          }`}>
                            {answerResult.isCorrect ? '🎉 Correct!' : '❌ Incorrect'}
                          </h4>
                          <p className={`text-sm mb-2 ${
                            answerResult.isCorrect ? 'text-green-700' : 'text-red-700'
                          }`}>
                            {answerResult.feedback}
                          </p>
                          {!answerResult.isCorrect && (
                            <div className="mt-3 pt-3 border-t border-red-200">
                              <p className="text-sm text-red-700">
                                <span className="font-semibold">Your answer:</span> <code className="bg-red-100 px-2 py-1 rounded">{studentAnswer}</code>
                              </p>
                              <p className="text-sm text-red-700">
                                <span className="font-semibold">Correct answer:</span> <code className="bg-red-100 px-2 py-1 rounded">{answerResult.correctAnswer}</code>
                              </p>
                            </div>
                          )}
                        </div>
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>

                {/* Hint */}
                {algorithmSteps.length > 0 && !showAnswer && !answerResult && (
                  <div className="text-xs text-gray-500 italic bg-blue-50 p-3 rounded border border-blue-200">
                    💡 Tip: Watch the algorithm steps carefully. The final step shows whether the target was found and at which index.
                  </div>
                )}
              </div>
            </motion.div>
          )}

          {/* Button to proceed to completion screen - only show when visualization is displayed and answer was correct */}
          {showVisualization && currentTask && taskResults[currentTask.id]?.isCorrect && !isCompleted && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3 }}
              className="mt-6 flex justify-center"
            >
              <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                onClick={() => setIsCompleted(true)}
                className="px-8 py-4 bg-gradient-to-r from-blue-600 to-indigo-600 text-white font-semibold text-lg rounded-xl hover:from-blue-700 hover:to-indigo-700 transition-all flex items-center justify-center gap-2 shadow-lg"
              >
                <Trophy className="w-5 h-5" />
                Continue to Great Page
              </motion.button>
            </motion.div>
          )}
        </motion.div>
        </div>
      )}

      {/* Show message if visualization is hidden */}
      {!showVisualization && currentTask && taskResults[currentTask.id]?.isCorrect && !isCompleted && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="text-center py-8 text-gray-600"
        >
          <p className="text-lg">Great job! The visualization will appear shortly...</p>
        </motion.div>
      )}

      {/* Completion Screen - Shows after correct answer and animation */}
      {isCompleted && (
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.5 }}
          className="fixed inset-0 bg-gradient-to-br from-indigo-900 via-purple-900 to-pink-900 flex items-center justify-center z-50"
        >
          <div className="bg-white rounded-3xl shadow-2xl p-12 max-w-md mx-4 text-center">
            <motion.div
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              transition={{ delay: 0.2, type: "spring", stiffness: 200 }}
              className="mb-6"
            >
              <Trophy className="w-24 h-24 text-yellow-500 mx-auto" />
            </motion.div>
            
            <h2 className="text-4xl font-bold text-gray-900 mb-4">
              🎉 Great Job! 🎉
            </h2>
            
            <p className="text-xl text-gray-700 mb-8">
              You answered correctly! The algorithm visualization has been completed.
            </p>

            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <button
                onClick={() => router.push('/')}
                className="px-8 py-4 rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 text-white font-semibold text-lg hover:from-blue-700 hover:to-indigo-700 transition-all flex items-center justify-center gap-2 shadow-lg"
              >
                <Home className="w-5 h-5" />
                Home
              </button>
              
              <button
                onClick={handleReset}
                className="px-8 py-4 rounded-xl border-2 border-gray-300 text-gray-700 font-semibold text-lg hover:bg-gray-50 transition-all flex items-center justify-center gap-2"
              >
                <RotateCcw className="w-5 h-5" />
                Attempt Again
              </button>
            </div>
          </div>
        </motion.div>
      )}
    </div>
  )
}
