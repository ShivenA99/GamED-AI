'use client'

import { useState, useEffect, useCallback } from 'react'
import CodeDisplay from './CodeDisplay'
import VariableTracker from './VariableTracker'
import StepControls from './StepControls'
import InteractiveTask from './InteractiveTask'

interface Step {
  index: number
  lineNumber: number
  description: string
  expectedVariables: Record<string, any>
}

interface Task {
  id: string
  type: 'variable_prediction' | 'multiple_choice' | 'free_response' | 'step_analysis'
  question?: string
  description?: string
  variable?: string
  correctAnswer?: string | number
  options?: Array<{ id: string; text: string; correct: boolean }>
  hint?: string
  feedbackCorrect?: string
  feedbackIncorrect?: string
  points?: number
  insertAfterStep?: number
}

interface AnimationCues {
  line_highlight_animation?: {
    duration: number
    effect: string
    color: string
  }
  variable_update_animation?: {
    duration: number
    effect: string
    easing: string
  }
}

interface Blueprint {
  templateType: string
  title: string
  narrativeIntro: string
  code: string
  language: string
  key_concepts?: string[]
  learningObjectives?: string[]
  steps: Step[]
  tasks: Task[]
  animationCues?: AnimationCues
  feedbackMessages?: {
    perfect?: string
    good?: string
    needsPractice?: string
  }
}

interface ScoreState {
  earned: number
  possible: number
  tasksCompleted: number
  hintsUsed: number
  streak: number
  maxStreak: number
}

interface StateTracerCodeGameProps {
  blueprint: Blueprint
  onComplete: (score: ScoreState) => void
  sessionId?: string
  theme?: 'dark' | 'light'
}

export default function StateTracerCodeGame({
  blueprint,
  onComplete,
  sessionId,
  theme = 'dark',
}: StateTracerCodeGameProps) {
  // State
  const [currentStepIndex, setCurrentStepIndex] = useState(0)
  const [executedLines, setExecutedLines] = useState<number[]>([])
  const [isPlaying, setIsPlaying] = useState(false)
  const [speed, setSpeed] = useState(1)
  const [previousVariables, setPreviousVariables] = useState<Record<string, any>>({})
  const [showTask, setShowTask] = useState(false)
  const [currentTaskIndex, setCurrentTaskIndex] = useState(0)
  const [taskAttempts, setTaskAttempts] = useState<Record<string, number>>({})
  const [taskHints, setTaskHints] = useState<Record<string, number>>({})
  const [completedTasks, setCompletedTasks] = useState<Set<string>>(new Set())
  const [gameComplete, setGameComplete] = useState(false)

  const [score, setScore] = useState<ScoreState>({
    earned: 0,
    possible: 0,
    tasksCompleted: 0,
    hintsUsed: 0,
    streak: 0,
    maxStreak: 0,
  })

  const steps = blueprint.steps || []
  const tasks = blueprint.tasks || []
  const currentStep = steps[currentStepIndex]
  const currentVariables = currentStep?.expectedVariables || {}

  // Check if there's a task for current step
  const currentStepTask = tasks.find(
    (t) =>
      (t.insertAfterStep === currentStepIndex || t.insertAfterStep === undefined) &&
      !completedTasks.has(t.id)
  )

  // Get all tasks that should be shown (for step_analysis type)
  const relevantTask = currentStepTask || tasks[currentTaskIndex]

  // Auto-play
  useEffect(() => {
    if (!isPlaying || gameComplete) return

    const interval = setInterval(() => {
      if (currentStepIndex < steps.length - 1 && !showTask) {
        handleNext()
      } else {
        setIsPlaying(false)
      }
    }, 2000 / speed)

    return () => clearInterval(interval)
  }, [isPlaying, currentStepIndex, steps.length, speed, showTask, gameComplete])

  // Track executed lines
  useEffect(() => {
    if (currentStep) {
      setExecutedLines((prev) => {
        if (!prev.includes(currentStep.lineNumber)) {
          return [...prev, currentStep.lineNumber]
        }
        return prev
      })
    }
  }, [currentStep])

  const handlePrev = useCallback(() => {
    if (currentStepIndex > 0) {
      setPreviousVariables(currentVariables)
      setCurrentStepIndex((prev) => prev - 1)
      setShowTask(false)
    }
  }, [currentStepIndex, currentVariables])

  const handleNext = useCallback(() => {
    if (showTask && relevantTask && !completedTasks.has(relevantTask.id)) {
      // Can't proceed until task is complete
      return
    }

    if (currentStepIndex < steps.length - 1) {
      setPreviousVariables(currentVariables)
      setCurrentStepIndex((prev) => prev + 1)
      setShowTask(false)

      // Check if next step has a task
      const nextStepTask = tasks.find(
        (t) => t.insertAfterStep === currentStepIndex + 1 && !completedTasks.has(t.id)
      )
      if (nextStepTask) {
        setTimeout(() => setShowTask(true), 500)
      }
    } else {
      // Game complete
      setGameComplete(true)
      onComplete(score)
    }
  }, [currentStepIndex, steps.length, currentVariables, showTask, relevantTask, completedTasks, tasks, score, onComplete])

  const handleReset = useCallback(() => {
    setCurrentStepIndex(0)
    setExecutedLines([])
    setIsPlaying(false)
    setPreviousVariables({})
    setShowTask(false)
    setCurrentTaskIndex(0)
    setTaskAttempts({})
    setTaskHints({})
    setCompletedTasks(new Set())
    setGameComplete(false)
    setScore({
      earned: 0,
      possible: 0,
      tasksCompleted: 0,
      hintsUsed: 0,
      streak: 0,
      maxStreak: 0,
    })
  }, [])

  const handleTaskAnswer = useCallback(
    (taskId: string, answer: any, correct: boolean, points: number = 10) => {
      setTaskAttempts((prev) => ({
        ...prev,
        [taskId]: (prev[taskId] || 0) + 1,
      }))

      if (correct) {
        setCompletedTasks((prev) => new Set([...prev, taskId]))

        // Calculate points with hint penalty
        const hints = taskHints[taskId] || 0
        const attempts = taskAttempts[taskId] || 0
        let earnedPoints = points
        earnedPoints -= hints * 2 // 2 points penalty per hint
        earnedPoints -= attempts * 1 // 1 point penalty per wrong attempt
        earnedPoints = Math.max(0, earnedPoints)

        setScore((prev) => ({
          ...prev,
          earned: prev.earned + earnedPoints,
          possible: prev.possible + points,
          tasksCompleted: prev.tasksCompleted + 1,
          streak: prev.streak + 1,
          maxStreak: Math.max(prev.maxStreak, prev.streak + 1),
        }))

        // Auto-advance after completing task
        setTimeout(() => {
          setShowTask(false)
          handleNext()
        }, 1500)
      } else {
        setScore((prev) => ({
          ...prev,
          streak: 0, // Reset streak on wrong answer
        }))
      }
    },
    [taskHints, taskAttempts, handleNext]
  )

  const handleHintRequest = useCallback((taskId: string) => {
    setTaskHints((prev) => ({
      ...prev,
      [taskId]: (prev[taskId] || 0) + 1,
    }))
    setScore((prev) => ({
      ...prev,
      hintsUsed: prev.hintsUsed + 1,
    }))
  }, [])

  // Completion screen
  if (gameComplete) {
    const percentage = score.possible > 0 ? Math.round((score.earned / score.possible) * 100) : 100
    const message =
      percentage >= 90
        ? blueprint.feedbackMessages?.perfect || 'Excellent work! You traced the code perfectly!'
        : percentage >= 70
        ? blueprint.feedbackMessages?.good || 'Good job! You understand most of the code execution.'
        : blueprint.feedbackMessages?.needsPractice || 'Keep practicing! Understanding code flow takes time.'

    return (
      <div className={`rounded-xl p-8 ${theme === 'dark' ? 'bg-gray-900' : 'bg-white'}`}>
        <div className="text-center">
          <div className="w-24 h-24 mx-auto mb-6 bg-gradient-to-br from-primary-500 to-secondary-500 rounded-full flex items-center justify-center">
            <span className="text-3xl font-bold text-white">{percentage}%</span>
          </div>
          <h2 className={`text-3xl font-bold mb-2 ${theme === 'dark' ? 'text-white' : 'text-gray-900'}`}>
            Code Tracing Complete!
          </h2>
          <p className={`text-lg mb-6 ${theme === 'dark' ? 'text-gray-300' : 'text-gray-600'}`}>
            {message}
          </p>

          {/* Stats */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
            <div className={`p-4 rounded-lg ${theme === 'dark' ? 'bg-gray-800' : 'bg-gray-100'}`}>
              <div className={`text-2xl font-bold ${theme === 'dark' ? 'text-white' : 'text-gray-900'}`}>
                {score.earned}
              </div>
              <div className={`text-sm ${theme === 'dark' ? 'text-gray-400' : 'text-gray-500'}`}>
                Points Earned
              </div>
            </div>
            <div className={`p-4 rounded-lg ${theme === 'dark' ? 'bg-gray-800' : 'bg-gray-100'}`}>
              <div className={`text-2xl font-bold ${theme === 'dark' ? 'text-white' : 'text-gray-900'}`}>
                {score.tasksCompleted}
              </div>
              <div className={`text-sm ${theme === 'dark' ? 'text-gray-400' : 'text-gray-500'}`}>
                Tasks Completed
              </div>
            </div>
            <div className={`p-4 rounded-lg ${theme === 'dark' ? 'bg-gray-800' : 'bg-gray-100'}`}>
              <div className={`text-2xl font-bold ${theme === 'dark' ? 'text-white' : 'text-gray-900'}`}>
                {score.maxStreak}
              </div>
              <div className={`text-sm ${theme === 'dark' ? 'text-gray-400' : 'text-gray-500'}`}>
                Best Streak
              </div>
            </div>
            <div className={`p-4 rounded-lg ${theme === 'dark' ? 'bg-gray-800' : 'bg-gray-100'}`}>
              <div className={`text-2xl font-bold ${theme === 'dark' ? 'text-white' : 'text-gray-900'}`}>
                {score.hintsUsed}
              </div>
              <div className={`text-sm ${theme === 'dark' ? 'text-gray-400' : 'text-gray-500'}`}>
                Hints Used
              </div>
            </div>
          </div>

          <div className="flex justify-center space-x-4">
            <button
              onClick={handleReset}
              className="px-6 py-3 bg-primary-500 text-white rounded-lg hover:bg-primary-600"
            >
              Try Again
            </button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className={`rounded-xl overflow-hidden ${theme === 'dark' ? 'bg-gray-900' : 'bg-white'}`}>
      {/* Header */}
      <div
        className={`px-6 py-4 border-b ${
          theme === 'dark' ? 'border-gray-700 bg-gray-800' : 'border-gray-200 bg-gray-50'
        }`}
      >
        <h2 className={`text-xl font-bold ${theme === 'dark' ? 'text-white' : 'text-gray-900'}`}>
          {blueprint.title}
        </h2>
        <p className={`text-sm mt-1 ${theme === 'dark' ? 'text-gray-400' : 'text-gray-600'}`}>
          {blueprint.narrativeIntro}
        </p>
      </div>

      {/* Score bar */}
      <div
        className={`px-6 py-2 flex items-center justify-between text-sm ${
          theme === 'dark' ? 'bg-gray-800/50' : 'bg-gray-100'
        }`}
      >
        <div className="flex items-center space-x-4">
          <span className={theme === 'dark' ? 'text-gray-300' : 'text-gray-600'}>
            Score: <span className="font-bold text-primary-500">{score.earned}</span>
          </span>
          {score.streak > 1 && (
            <span className="text-yellow-500 flex items-center">
              <svg className="w-4 h-4 mr-1" fill="currentColor" viewBox="0 0 20 20">
                <path d="M12.395 2.553a1 1 0 00-1.45-.385c-.345.23-.614.558-.822.88-.214.33-.403.713-.57 1.116-.334.804-.614 1.768-.84 2.734a31.365 31.365 0 00-.613 3.58 2.64 2.64 0 01-.945-1.067c-.328-.68-.398-1.534-.398-2.654A1 1 0 005.05 6.05 6.981 6.981 0 003 11a7 7 0 1011.95-4.95c-.592-.591-.98-.985-1.348-1.467-.363-.476-.724-1.063-1.207-2.03zM12.12 15.12A3 3 0 017 13s.879.5 2.5.5c0-1 .5-4 1.25-4.5.5 1 .786 1.293 1.371 1.879A2.99 2.99 0 0113 13a2.99 2.99 0 01-.879 2.121z" />
              </svg>
              {score.streak}x Streak
            </span>
          )}
        </div>
        <div className={`flex items-center space-x-2 ${theme === 'dark' ? 'text-gray-400' : 'text-gray-500'}`}>
          {blueprint.key_concepts?.slice(0, 3).map((concept, i) => (
            <span key={i} className={`px-2 py-1 rounded text-xs ${
              theme === 'dark' ? 'bg-gray-700' : 'bg-gray-200'
            }`}>
              {concept}
            </span>
          ))}
        </div>
      </div>

      {/* Main content */}
      <div className="p-6">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Code panel (2/3 width) */}
          <div className="lg:col-span-2 space-y-4">
            <CodeDisplay
              code={blueprint.code}
              language={blueprint.language || 'python'}
              currentLine={currentStep?.lineNumber || 1}
              executedLines={executedLines}
              theme={theme}
            />

            {/* Step description */}
            {currentStep && (
              <div
                className={`p-4 rounded-lg ${
                  theme === 'dark' ? 'bg-gray-800' : 'bg-gray-100'
                }`}
              >
                <div className="flex items-start">
                  <div
                    className={`
                      w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 mr-3
                      bg-gradient-to-br from-primary-500 to-secondary-500 text-white font-bold text-sm
                    `}
                  >
                    {currentStepIndex + 1}
                  </div>
                  <div>
                    <p className={`font-medium ${theme === 'dark' ? 'text-white' : 'text-gray-900'}`}>
                      Line {currentStep.lineNumber}
                    </p>
                    <p className={`mt-1 ${theme === 'dark' ? 'text-gray-300' : 'text-gray-600'}`}>
                      {currentStep.description}
                    </p>
                  </div>
                </div>
              </div>
            )}

            {/* Interactive task */}
            {showTask && relevantTask && !completedTasks.has(relevantTask.id) && (
              <InteractiveTask
                task={relevantTask}
                onAnswer={(answer, correct) =>
                  handleTaskAnswer(relevantTask.id, answer, correct, relevantTask.points || 10)
                }
                onHintRequest={() => handleHintRequest(relevantTask.id)}
                hintsUsed={taskHints[relevantTask.id] || 0}
                attempts={taskAttempts[relevantTask.id] || 0}
                theme={theme}
              />
            )}
          </div>

          {/* Variables panel (1/3 width) */}
          <div className="space-y-4">
            <VariableTracker
              variables={currentVariables}
              previousVariables={previousVariables}
              highlightChanges={true}
              showHistory={true}
              theme={theme}
            />

            {/* Learning objectives */}
            {blueprint.learningObjectives && (
              <div
                className={`p-4 rounded-lg ${
                  theme === 'dark' ? 'bg-gray-800' : 'bg-gray-100'
                }`}
              >
                <h4 className={`text-sm font-semibold mb-2 ${
                  theme === 'dark' ? 'text-gray-300' : 'text-gray-700'
                }`}>
                  Learning Objectives
                </h4>
                <ul className="space-y-1">
                  {blueprint.learningObjectives.map((obj, i) => (
                    <li
                      key={i}
                      className={`text-xs flex items-start ${
                        theme === 'dark' ? 'text-gray-400' : 'text-gray-600'
                      }`}
                    >
                      <svg
                        className="w-4 h-4 mr-1 text-green-500 flex-shrink-0"
                        fill="currentColor"
                        viewBox="0 0 20 20"
                      >
                        <path
                          fillRule="evenodd"
                          d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                          clipRule="evenodd"
                        />
                      </svg>
                      {obj}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>

        {/* Step controls */}
        <div className="mt-6">
          <StepControls
            currentStep={currentStepIndex}
            totalSteps={steps.length}
            isPlaying={isPlaying}
            speed={speed}
            onPrev={handlePrev}
            onNext={handleNext}
            onPlay={() => setIsPlaying(true)}
            onPause={() => setIsPlaying(false)}
            onReset={handleReset}
            onSpeedChange={setSpeed}
            disabled={showTask && relevantTask && !completedTasks.has(relevantTask.id)}
            theme={theme}
          />
        </div>
      </div>
    </div>
  )
}
