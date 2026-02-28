'use client'

import { useState, useEffect, useCallback, useMemo, use } from 'react'
import { useRouter } from 'next/navigation'
import { useTheme } from 'next-themes'
import dynamic from 'next/dynamic'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { parseBlueprint } from '@/components/templates/InteractiveDiagramGame/engine/schemas/parseBlueprint'

// Lazy load heavy game template components for better code splitting
const StateTracerCodeGame = dynamic(
  () => import('@/components/templates/StateTracerCodeGame'),
  {
    loading: () => <GameLoadingSkeleton templateType="Code Tracer" />,
    ssr: false,
  }
)

const InteractiveDiagramGame = dynamic(
  () => import('@/components/templates/InteractiveDiagramGame'),
  {
    loading: () => <GameLoadingSkeleton templateType="Label Diagram" />,
    ssr: false,
  }
)

const PhetSimulationGame = dynamic(
  () => import('@/components/templates/PhetSimulationGame').then(mod => ({ default: mod.PhetSimulationGame })),
  {
    loading: () => <GameLoadingSkeleton templateType="PhET Simulation" />,
    ssr: false,
  }
)

const StateTracerGame = dynamic(
  () => import('@/components/templates/AlgorithmGame/StateTracerGame'),
  {
    loading: () => <GameLoadingSkeleton templateType="Algorithm Game" />,
    ssr: false,
  }
)

const BugHunterGame = dynamic(
  () => import('@/components/templates/AlgorithmGame/BugHunterGame'),
  {
    loading: () => <GameLoadingSkeleton templateType="Bug Hunter" />,
    ssr: false,
  }
)

const AlgorithmBuilderGame = dynamic(
  () => import('@/components/templates/AlgorithmGame/AlgorithmBuilderGame'),
  {
    loading: () => <GameLoadingSkeleton templateType="Algorithm Builder" />,
    ssr: false,
  }
)

const ComplexityAnalyzerGame = dynamic(
  () => import('@/components/templates/AlgorithmGame/ComplexityAnalyzerGame'),
  {
    loading: () => <GameLoadingSkeleton templateType="Complexity Analyzer" />,
    ssr: false,
  }
)

const ConstraintPuzzleGame = dynamic(
  () => import('@/components/templates/AlgorithmGame/ConstraintPuzzleGame'),
  {
    loading: () => <GameLoadingSkeleton templateType="Constraint Puzzle" />,
    ssr: false,
  }
)

const AlgorithmMultiSceneGame = dynamic(
  () => import('@/components/templates/AlgorithmGame/AlgorithmMultiSceneGame'),
  {
    loading: () => <GameLoadingSkeleton templateType="Algorithm Game" />,
    ssr: false,
  }
)

const ModeToggle = dynamic(
  () => import('@/components/templates/AlgorithmGame/components/ModeToggle'),
  { ssr: false }
)

// Loading skeleton component for game templates
function GameLoadingSkeleton({ templateType }: { templateType: string }) {
  return (
    <div className="space-y-6 p-6">
      <div className="flex items-center gap-3 mb-6">
        <Skeleton className="h-8 w-8 rounded-lg" />
        <div className="space-y-2">
          <Skeleton className="h-6 w-48" />
          <Skeleton className="h-4 w-32" />
        </div>
      </div>
      <Skeleton className="h-64 w-full rounded-xl" />
      <div className="flex items-center justify-between">
        <Skeleton className="h-4 w-24" />
        <Skeleton className="h-10 w-32 rounded-lg" />
      </div>
      <p className="text-center text-sm text-muted-foreground">
        Loading {templateType} game...
      </p>
    </div>
  )
}

interface GameTask {
  id: string
  questionText?: string
  question?: string
  correctAnswer?: string | number
  targetValues?: Record<string, number>
  options?: string[]
  feedback?: { correct?: string; incorrect?: string }
}

interface GameStep {
  id: string
  text: string
  order: number
}

interface GameParameter {
  id: string
  name: string
  label?: string
  min: number
  max: number
  default: number
  defaultValue?: number
  step?: number
  unit?: string
}

interface FeedbackMessages {
  perfect?: string
  good?: string
  retry?: string
}

interface GameBlueprint {
  templateType: string
  title: string
  narrativeIntro: string
  tasks?: GameTask[]
  steps?: GameStep[]
  pairs?: Array<{ term: string; definition: string }>
  buckets?: Array<{ id: string; name: string; items: string[] }>
  items?: Array<{ id: string; text: string; category?: string }>
  parameters?: GameParameter[]
  visualization?: Record<string, unknown>
  hints?: Array<{ text: string; hintText?: string; forZone?: string; taskId?: string }>
  feedbackMessages?: FeedbackMessages
  [key: string]: unknown
}

interface GameStatus {
  status: 'pending' | 'running' | 'completed' | 'failed'
  current_step?: string
  blueprint?: GameBlueprint
  error?: string
}

/**
 * Wrapper that memoizes the parseBlueprint result so the InteractiveDiagramGame
 * receives a stable blueprint reference and doesn't re-initialize on parent re-renders.
 */
function InteractiveDiagramWrapper({ blueprint, processId }: { blueprint: GameBlueprint; processId: string }) {
  const { blueprint: validatedBp, errors: bpErrors } = useMemo(
    () => parseBlueprint(blueprint),
    [blueprint]
  )
  if (bpErrors.length > 0) {
    console.warn('[GamePage] Blueprint validation errors:', bpErrors)
  }
  return (
    <div className="max-w-4xl mx-auto p-4">
      <InteractiveDiagramGame
        blueprint={validatedBp}
        onComplete={() => {
          // Game completion handled by component
        }}
        sessionId={processId}
      />
    </div>
  )
}

export default function GamePage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params)
  const router = useRouter()
  const { resolvedTheme } = useTheme()
  const processId = id

  const [status, setStatus] = useState<GameStatus>({ status: 'pending' })
  const [gameStarted, setGameStarted] = useState(false)
  const [currentTaskIndex, setCurrentTaskIndex] = useState(0)
  const [score, setScore] = useState(0)
  const [showResults, setShowResults] = useState(false)
  const [userInput, setUserInput] = useState<string>('')
  const [feedback, setFeedback] = useState<{ correct: boolean; message: string } | null>(null)

  // For SEQUENCE_BUILDER
  const [orderedSteps, setOrderedSteps] = useState<any[]>([])

  // For BUCKET_SORT
  const [bucketAssignments, setBucketAssignments] = useState<Record<string, string>>({})

  // For PARAMETER_PLAYGROUND
  const [paramValues, setParamValues] = useState<Record<string, number>>({})

  // For ALGORITHM_GAME mode toggle
  const [algorithmGameMode, setAlgorithmGameMode] = useState<'learn' | 'test'>('learn')

  const pollStatus = useCallback(async () => {
    try {
      const response = await fetch(`/api/status/${processId}`)
      const data = await response.json()
      setStatus(data)
      return data.status === 'completed' || data.status === 'failed'
    } catch (error) {
      console.error('Error polling status:', error)
      return false
    }
  }, [processId])

  useEffect(() => {
    let interval: NodeJS.Timeout

    const startPolling = async () => {
      const done = await pollStatus()
      if (!done) {
        interval = setInterval(async () => {
          const done = await pollStatus()
          if (done) {
            clearInterval(interval)
          }
        }, 2000)
      }
    }

    startPolling()

    return () => {
      if (interval) clearInterval(interval)
    }
  }, [pollStatus])

  // Initialize game state when blueprint loads
  useEffect(() => {
    if (status.blueprint) {
      const bp = status.blueprint

      // Initialize SEQUENCE_BUILDER
      if (bp.templateType === 'SEQUENCE_BUILDER' && bp.steps) {
        // Shuffle steps for the user to reorder
        const shuffled = [...bp.steps].sort(() => Math.random() - 0.5)
        setOrderedSteps(shuffled)
      }

      // Initialize PARAMETER_PLAYGROUND
      if (bp.templateType === 'PARAMETER_PLAYGROUND' && bp.parameters) {
        const initial: Record<string, number> = {}
        bp.parameters.forEach((p: GameParameter) => {
          initial[p.id] = p.default
        })
        setParamValues(initial)
      }
    }
  }, [status.blueprint])

  const handleStartGame = () => {
    setGameStarted(true)
  }

  const handleSubmitAnswer = () => {
    const blueprint = status.blueprint
    if (!blueprint) return

    const task = blueprint.tasks?.[currentTaskIndex]
    if (!task) return

    let isCorrect = false
    let message = ''

    // Check answer based on template type
    if (blueprint.templateType === 'PARAMETER_PLAYGROUND') {
      // Check if parameter values match target
      const targetValues = task.targetValues || {}
      isCorrect = Object.keys(targetValues).every(
        key => paramValues[key] === targetValues[key]
      )
      message = isCorrect
        ? blueprint.feedbackMessages?.perfect || 'Correct!'
        : blueprint.feedbackMessages?.retry || 'Not quite. Try adjusting the parameters.'
    } else if (task.correctAnswer) {
      // Simple text comparison
      isCorrect = userInput.toLowerCase().trim() === String(task.correctAnswer).toLowerCase().trim()
      message = isCorrect ? 'Correct!' : `The answer was: ${task.correctAnswer}`
    }

    setFeedback({ correct: isCorrect, message })
    if (isCorrect) {
      setScore(prev => prev + 10)
    }
  }

  const handleNextTask = () => {
    const tasks = status.blueprint?.tasks || []
    if (currentTaskIndex < tasks.length - 1) {
      setCurrentTaskIndex(prev => prev + 1)
      setFeedback(null)
      setUserInput('')
    } else {
      setShowResults(true)
    }
  }

  const handleRestart = () => {
    setGameStarted(false)
    setCurrentTaskIndex(0)
    setScore(0)
    setShowResults(false)
    setUserInput('')
    setFeedback(null)
    setOrderedSteps([])
    setBucketAssignments({})

    // Re-initialize
    if (status.blueprint?.steps) {
      const shuffled = [...status.blueprint.steps].sort(() => Math.random() - 0.5)
      setOrderedSteps(shuffled)
    }
  }

  // Loading state
  if (status.status === 'pending' || status.status === 'running') {
    return (
      <div className="min-h-[60vh] flex flex-col items-center justify-center px-4">
        <div className="text-center">
          <div className="relative w-24 h-24 mx-auto mb-6">
            <div className="absolute inset-0 border-4 border-primary/20 rounded-full"></div>
            <div className="absolute inset-0 border-4 border-primary rounded-full animate-spin border-t-transparent"></div>
            <div className="absolute inset-4 bg-gradient-to-br from-primary to-secondary rounded-full pulse-ring"></div>
          </div>
          <h2 className="text-2xl font-bold text-foreground mb-2">Generating Your Game</h2>
          <p className="text-muted-foreground mb-4">
            {status.current_step || 'Analyzing your question...'}
          </p>
          <div className="flex items-center justify-center space-x-2 text-sm text-muted-foreground">
            <span>Process ID:</span>
            <code className="bg-muted px-2 py-1 rounded">{processId}</code>
          </div>
        </div>
      </div>
    )
  }

  // Error state
  if (status.status === 'failed') {
    return (
      <div className="min-h-[60vh] flex flex-col items-center justify-center px-4">
        <div className="text-center max-w-md">
          <div className="w-16 h-16 bg-destructive/10 rounded-full flex items-center justify-center mx-auto mb-4">
            <svg className="w-8 h-8 text-destructive" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </div>
          <h2 className="text-2xl font-bold text-foreground mb-2">Generation Failed</h2>
          <p className="text-muted-foreground mb-4">{status.error || 'An error occurred while generating your game.'}</p>
          <Button onClick={() => router.push('/')}>
            Try Again
          </Button>
        </div>
      </div>
    )
  }

  const blueprint = status.blueprint as GameBlueprint | undefined

  if (!blueprint) {
    return (
      <div className="text-center py-12 px-4">
        <p className="text-muted-foreground">No game data available.</p>
      </div>
    )
  }

  // ALGORITHM_GAME - All 5 algorithm game types + multi-scene
  if (blueprint.templateType === 'ALGORITHM_GAME') {
    const theme = (resolvedTheme as 'dark' | 'light') || 'dark'
    const onComplete = () => { /* Game completion handled by component */ }

    // Multi-scene: use orchestrator
    if (blueprint.is_multi_scene && blueprint.scenes) {
      return (
        <div className="max-w-6xl mx-auto p-4">
          <AlgorithmMultiSceneGame
            blueprint={blueprint as never}
            onComplete={onComplete}
            theme={theme}
          />
        </div>
      )
    }

    // Single-scene: route by algorithmGameType
    const gameType = blueprint.algorithmGameType || 'state_tracer'

    // Extract the sub-blueprint for the specific game type, falling back to the whole blueprint
    const subBlueprint = (
      gameType === 'state_tracer' ? blueprint.stateTracerBlueprint :
      gameType === 'bug_hunter' ? blueprint.bugHunterBlueprint :
      gameType === 'algorithm_builder' ? blueprint.algorithmBuilderBlueprint :
      gameType === 'complexity_analyzer' ? blueprint.complexityAnalyzerBlueprint :
      gameType === 'constraint_puzzle' ? blueprint.constraintPuzzleBlueprint :
      blueprint
    ) || blueprint

    const GameComponent = (
      gameType === 'bug_hunter' ? BugHunterGame :
      gameType === 'algorithm_builder' ? AlgorithmBuilderGame :
      gameType === 'complexity_analyzer' ? ComplexityAnalyzerGame :
      gameType === 'constraint_puzzle' ? ConstraintPuzzleGame :
      StateTracerGame
    )

    return (
      <div className="max-w-6xl mx-auto p-4">
        <div className="flex justify-end mb-3">
          <ModeToggle mode={algorithmGameMode} onToggle={setAlgorithmGameMode} />
        </div>
        <GameComponent
          blueprint={subBlueprint as never}
          onComplete={onComplete}
          theme={theme}
          gameplayMode={algorithmGameMode}
        />
      </div>
    )
  }

  // BUG_HUNTER - Bug finding game (legacy templateType)
  if (blueprint.templateType === 'BUG_HUNTER') {
    return (
      <div className="max-w-6xl mx-auto p-4">
        <BugHunterGame
          blueprint={blueprint as never}
          onComplete={() => {
            // Game completion handled by component
          }}
          theme={(resolvedTheme as 'dark' | 'light') || 'dark'}
        />
      </div>
    )
  }

  // STATE_TRACER_CODE - Use specialized component
  if (blueprint.templateType === 'STATE_TRACER_CODE') {
    return (
      <div className="max-w-6xl mx-auto p-4">
        <StateTracerCodeGame
          blueprint={blueprint as never}
          onComplete={() => {
            // Game completion handled by component
          }}
          sessionId={processId}
          theme="dark"
        />
      </div>
    )
  }

  // INTERACTIVE_DIAGRAM - Use specialized component (also accept legacy LABEL_DIAGRAM)
  if (blueprint.templateType === 'INTERACTIVE_DIAGRAM' || blueprint.templateType === 'LABEL_DIAGRAM') {
    return (
      <InteractiveDiagramWrapper blueprint={blueprint} processId={processId} />
    )
  }

  // PHET_SIMULATION - Use specialized component
  if (blueprint.templateType === 'PHET_SIMULATION') {
    return (
      <div className="max-w-6xl mx-auto p-4">
        <PhetSimulationGame
          blueprint={blueprint as never}
          onComplete={() => {
            // Game completion tracked via analytics if configured
          }}
          onProgress={() => {
            // Progress tracking via analytics if configured
          }}
        />
      </div>
    )
  }

  // Results screen
  if (showResults) {
    const tasks = blueprint.tasks || []
    const maxScore = tasks.length * 10
    const percentage = maxScore > 0 ? Math.round((score / maxScore) * 100) : 0

    return (
      <div className="game-container">
        <div className="text-center py-8">
          <div className="w-20 h-20 bg-gradient-to-br from-primary to-secondary rounded-full flex items-center justify-center mx-auto mb-4">
            <span className="text-3xl font-bold text-white">{percentage}%</span>
          </div>
          <h2 className="text-3xl font-bold text-foreground mb-2">Game Complete!</h2>
          <p className="text-xl text-muted-foreground mb-4">
            You scored {score} out of {maxScore} points
          </p>
          <p className="text-muted-foreground mb-6">
            {blueprint.feedbackMessages?.perfect || 'Great job completing the game!'}
          </p>
          <div className="flex flex-col sm:flex-row justify-center gap-3 mt-6">
            <Button onClick={handleRestart} size="lg" className="min-h-[44px]">
              Play Again
            </Button>
            <Button variant="secondary" onClick={() => router.push('/')} size="lg" className="min-h-[44px]">
              New Game
            </Button>
          </div>
        </div>
      </div>
    )
  }

  // Intro screen
  if (!gameStarted) {
    return (
      <div className="game-container">
        <div className="text-center py-8">
          <Badge variant="info" className="mb-4">
            {blueprint.templateType?.replace(/_/g, ' ')}
          </Badge>
          <h1 className="game-title text-3xl">{blueprint.title}</h1>
          <p className="game-narrative max-w-2xl mx-auto">{blueprint.narrativeIntro}</p>

          {blueprint.tasks && (
            <p className="text-muted-foreground mb-6">
              {blueprint.tasks.length} task{blueprint.tasks.length !== 1 ? 's' : ''} to complete
            </p>
          )}

          <Button
            onClick={handleStartGame}
            size="xl"
            className="bg-gradient-to-r from-primary to-secondary hover:from-primary/90 hover:to-secondary/90 shadow-lg hover:shadow-xl transition-all min-h-[44px]"
          >
            Start Game
          </Button>
        </div>
      </div>
    )
  }

  // Game play screen - render based on template type
  const tasks = blueprint.tasks || []
  const currentTask = tasks[currentTaskIndex]

  if (!currentTask) {
    // No tasks - show completion
    return (
      <div className="game-container">
        <div className="text-center py-8">
          <h2 className="text-2xl font-bold text-foreground mb-4">Explore the Game</h2>
          <p className="text-muted-foreground mb-6">{blueprint.narrativeIntro}</p>

          {/* Render PARAMETER_PLAYGROUND visualization */}
          {blueprint.templateType === 'PARAMETER_PLAYGROUND' && blueprint.parameters && (
            <div className="space-y-6 text-left max-w-xl mx-auto">
              <h3 className="font-semibold text-lg text-foreground">Adjust Parameters:</h3>
              {blueprint.parameters.map((param: GameParameter) => (
                <div key={param.id} className="space-y-2">
                  <label className="block text-sm font-medium text-foreground">
                    {param.label}: {paramValues[param.id]} {param.unit || ''}
                  </label>
                  <input
                    type="range"
                    min={param.min || 0}
                    max={param.max || 100}
                    step={param.step || 1}
                    value={paramValues[param.id] || param.defaultValue}
                    onChange={(e) => setParamValues(prev => ({
                      ...prev,
                      [param.id]: Number(e.target.value)
                    }))}
                    className="w-full accent-primary"
                    aria-label={`${param.label} slider`}
                  />
                </div>
              ))}
            </div>
          )}

          <Button onClick={() => setShowResults(true)} className="mt-6 min-h-[44px]">
            Finish
          </Button>
        </div>
      </div>
    )
  }

  // Render task based on type
  const renderTask = () => {
    const taskQuestion = currentTask.questionText || currentTask.question || 'Complete this task'

    return (
      <div className="task-card">
        <h3 className="text-xl font-semibold text-foreground mb-4">{taskQuestion}</h3>

        {/* PARAMETER_PLAYGROUND - show sliders */}
        {blueprint.templateType === 'PARAMETER_PLAYGROUND' && blueprint.parameters && (
          <div className="space-y-6 mb-6">
            {blueprint.parameters.map((param: GameParameter) => (
              <div key={param.id} className="space-y-2">
                <label className="block text-sm font-medium text-foreground">
                  {param.label}: <span className="text-primary font-bold">{paramValues[param.id]}</span> {param.unit || ''}
                </label>
                <input
                  type="range"
                  min={param.min || 0}
                  max={param.max || 100}
                  step={param.step || 1}
                  value={paramValues[param.id] || param.defaultValue}
                  onChange={(e) => setParamValues(prev => ({
                    ...prev,
                    [param.id]: Number(e.target.value)
                  }))}
                  className="w-full h-2 bg-muted rounded-lg appearance-none cursor-pointer accent-primary"
                  disabled={!!feedback}
                  aria-label={`${param.label} slider`}
                />
                <div className="flex justify-between text-xs text-muted-foreground">
                  <span>{param.min || 0}</span>
                  <span>{param.max || 100}</span>
                </div>
              </div>
            ))}

            {currentTask.targetValues && (
              <div className="bg-info-bg dark:bg-info/10 p-4 rounded-lg">
                <p className="text-sm text-info">
                  <strong>Target:</strong> {Object.entries(currentTask.targetValues).map(([k, v]) => `${k} = ${v}`).join(', ')}
                </p>
              </div>
            )}
          </div>
        )}

        {/* Options-based tasks (MCQ) */}
        {currentTask.options && (
          <div className="space-y-3">
            {currentTask.options.map((option: string, index: number) => {
              const isSelected = userInput === option
              const isCorrect = feedback && option === currentTask.correctAnswer
              const isWrong = feedback && isSelected && !feedback.correct

              let btnClass = 'option-button'
              if (isCorrect) btnClass = 'option-button correct'
              else if (isWrong) btnClass = 'option-button incorrect'
              else if (isSelected) btnClass = 'option-button selected'

              return (
                <button
                  key={index}
                  onClick={() => !feedback && setUserInput(option)}
                  disabled={!!feedback}
                  className={btnClass}
                  aria-pressed={isSelected}
                >
                  <span className="flex items-center">
                    <span className="w-8 h-8 rounded-full bg-muted flex items-center justify-center mr-3 text-sm font-medium">
                      {String.fromCharCode(65 + index)}
                    </span>
                    {option}
                  </span>
                </button>
              )
            })}
          </div>
        )}

        {/* Text input for other task types */}
        {!currentTask.options && blueprint.templateType !== 'PARAMETER_PLAYGROUND' && (
          <div className="space-y-4">
            <input
              type="text"
              value={userInput}
              onChange={(e) => setUserInput(e.target.value)}
              placeholder="Enter your answer..."
              disabled={!!feedback}
              className="w-full p-3 border-2 border-input bg-background text-foreground rounded-lg focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
              aria-label="Your answer"
            />
          </div>
        )}

        {/* Hints */}
        {blueprint.hints && blueprint.hints.length > 0 && !feedback && (
          <details className="mt-4">
            <summary className="text-sm text-primary cursor-pointer hover:underline">Need a hint?</summary>
            <p className="mt-2 text-sm text-foreground bg-warning-bg dark:bg-warning/10 p-3 rounded-lg">
              {blueprint.hints.find((h) => h.taskId === currentTask.id)?.hintText || 'Think carefully about the question.'}
            </p>
          </details>
        )}

        {/* Feedback */}
        {feedback && (
          <div className={`mt-4 p-4 rounded-lg ${feedback.correct ? 'bg-success-bg dark:bg-success/10 text-success' : 'bg-error-bg dark:bg-error/10 text-error'}`}>
            <p className="font-medium">{feedback.message}</p>
          </div>
        )}
      </div>
    )
  }

  return (
    <div className="game-container">
      {/* Progress bar */}
      <div className="mb-6">
        <div className="flex justify-between text-sm text-muted-foreground mb-2">
          <span>Task {currentTaskIndex + 1} of {tasks.length}</span>
          <span>Score: {score}</span>
        </div>
        <div className="h-2 bg-muted rounded-full overflow-hidden" role="progressbar" aria-valuenow={currentTaskIndex + (feedback ? 1 : 0)} aria-valuemin={0} aria-valuemax={tasks.length}>
          <div
            className="h-full bg-gradient-to-r from-primary to-secondary transition-all"
            style={{ width: `${((currentTaskIndex + (feedback ? 1 : 0)) / tasks.length) * 100}%` }}
          />
        </div>
      </div>

      {renderTask()}

      {/* Actions */}
      <div className="mt-6 flex flex-col sm:flex-row justify-end gap-3">
        {!feedback && (
          <Button onClick={handleSubmitAnswer} className="min-h-[44px]">
            Submit Answer
          </Button>
        )}
        {feedback && (
          <Button onClick={handleNextTask} className="min-h-[44px]">
            {currentTaskIndex < tasks.length - 1 ? 'Next Task' : 'See Results'}
            <svg className="w-5 h-5 ml-2" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
            </svg>
          </Button>
        )}
      </div>
    </div>
  )
}
