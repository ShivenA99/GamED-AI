/**
 * PhET Simulation Game Component
 *
 * Main component that renders PhET simulations with assessment wrapper.
 * Follows the same pattern as InteractiveDiagramGame.
 */

import React, { useEffect, useCallback, useMemo } from 'react';
import {
  PhetSimulationBlueprint,
  GameResults,
  GameProgress,
  PhetInteraction,
  Checkpoint,
  AssessmentTask
} from './types';
import { usePhetSimulationState, evaluateCheckpoint } from './hooks/usePhetSimulationState';
import { usePhetBridge, getPhetSimulationUrl } from './hooks/usePhetBridge';

// =============================================================================
// MAIN COMPONENT
// =============================================================================

interface PhetSimulationGameProps {
  blueprint: PhetSimulationBlueprint;
  onComplete?: (results: GameResults) => void;
  onProgress?: (progress: GameProgress) => void;
}

export function PhetSimulationGame({ blueprint, onComplete, onProgress }: PhetSimulationGameProps) {
  // Normalize blueprint
  const normalizedBlueprint = useMemo(() => normalizeBlueprint(blueprint), [blueprint]);

  // Game state management
  const {
    gameState,
    currentTaskIndex,
    currentTask,
    completedCheckpoints,
    score,
    maxScore,
    hintsUsed,
    isComplete,
    completeCheckpoint,
    useHint,
    nextTask,
    trackStateChange,
    trackInteraction,
    resetGame,
    revealedHints,
    isTaskComplete
  } = usePhetSimulationState(normalizedBlueprint);

  // PhET bridge for simulation communication
  const {
    iframeRef,
    isReady,
    simulationState,
    interactions,
    reset: resetSimulation
  } = usePhetBridge({
    bridgeConfig: normalizedBlueprint.bridgeConfig,
    onStateChange: (property, value, oldValue) => {
      trackStateChange(property, value);
    },
    onInteraction: (interaction) => {
      trackInteraction(interaction);
    }
  });

  // Evaluate checkpoints when state/interactions change
  useEffect(() => {
    if (!currentTask || !isReady) return;

    currentTask.checkpoints.forEach(checkpoint => {
      if (completedCheckpoints.has(checkpoint.id)) return;

      // Check if previous checkpoint is required
      if (checkpoint.requiresPrevious && !completedCheckpoints.has(checkpoint.requiresPrevious)) {
        return;
      }

      const isSatisfied = evaluateCheckpoint(
        checkpoint,
        simulationState,
        interactions,
        gameState
      );

      if (isSatisfied) {
        completeCheckpoint(checkpoint.id, checkpoint.points);
      }
    });
  }, [simulationState, interactions, currentTask, completedCheckpoints, isReady, gameState, completeCheckpoint]);

  // Report progress
  useEffect(() => {
    onProgress?.({
      currentTaskIndex,
      totalTasks: normalizedBlueprint.tasks.length,
      completedCheckpoints: Array.from(completedCheckpoints),
      score,
      maxScore,
      timeElapsedSeconds: Math.floor((Date.now() - gameState.startTime) / 1000)
    });
  }, [currentTaskIndex, completedCheckpoints, score, maxScore, gameState.startTime, normalizedBlueprint.tasks.length, onProgress]);

  // Handle completion
  useEffect(() => {
    if (isComplete) {
      onComplete?.({
        finalScore: score,
        maxScore,
        completedCheckpoints: Array.from(completedCheckpoints),
        completedTasks: Array.from(gameState.completedTasks),
        hintsUsed,
        timeSpentSeconds: Math.floor((Date.now() - gameState.startTime) / 1000),
        explorationMetrics: {
          uniqueParameterValues: Object.fromEntries(
            Array.from(gameState.exploredValues.entries()).map(([k, v]) => [k, v.size])
          ),
          totalInteractions: interactions.length,
          discoveredRelationships: []
        }
      });
    }
  }, [isComplete, score, maxScore, completedCheckpoints, gameState, hintsUsed, interactions.length, onComplete]);

  // Reset handler
  const handleRestart = useCallback(() => {
    resetGame();
    resetSimulation();
  }, [resetGame, resetSimulation]);

  // Simulation URL
  const simulationUrl = useMemo(() => {
    return getPhetSimulationUrl(
      normalizedBlueprint.simulation.simulationId,
      normalizedBlueprint.simulation.localPath,
      normalizedBlueprint.simulation.screen
    );
  }, [normalizedBlueprint.simulation]);

  // Results screen
  if (isComplete) {
    return (
      <ResultsPanel
        score={score}
        maxScore={maxScore}
        feedback={normalizedBlueprint.feedback}
        results={{
          finalScore: score,
          maxScore,
          completedCheckpoints: Array.from(completedCheckpoints),
          completedTasks: Array.from(gameState.completedTasks),
          hintsUsed,
          timeSpentSeconds: Math.floor((Date.now() - gameState.startTime) / 1000)
        }}
        onRestart={handleRestart}
      />
    );
  }

  return (
    <div className="phet-game-container flex flex-col lg:flex-row gap-4 h-full min-h-[600px] p-4 bg-gray-50">
      {/* Simulation Panel */}
      <div className="flex-1 flex flex-col min-w-0">
        <div className="bg-white rounded-lg shadow-md overflow-hidden flex-1 flex flex-col">
          {/* Header */}
          <div className="bg-gradient-to-r from-blue-600 to-blue-700 text-white p-4">
            <h1 className="text-xl font-bold">{normalizedBlueprint.title}</h1>
            <p className="text-blue-100 text-sm mt-1">{normalizedBlueprint.narrativeIntro}</p>
          </div>

          {/* Simulation Frame */}
          <div className="flex-1 relative bg-gray-100">
            {!isReady && (
              <div className="absolute inset-0 flex items-center justify-center bg-gray-100 z-10">
                <div className="text-center">
                  <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
                  <p className="text-gray-600">Loading simulation...</p>
                </div>
              </div>
            )}
            <iframe
              ref={iframeRef}
              src={simulationUrl}
              className="w-full h-full border-0"
              title={`PhET Simulation: ${normalizedBlueprint.simulation.simulationId}`}
              allow="fullscreen"
              sandbox="allow-scripts allow-same-origin allow-popups"
            />
          </div>
        </div>
      </div>

      {/* Assessment Panel */}
      <div className="w-full lg:w-96 flex flex-col gap-4">
        {/* Score Panel */}
        <ScorePanel
          score={score}
          maxScore={maxScore}
          currentTask={currentTaskIndex + 1}
          totalTasks={normalizedBlueprint.tasks.length}
        />

        {/* Task Panel */}
        {currentTask && (
          <TaskPanel
            task={currentTask}
            completedCheckpoints={completedCheckpoints}
            hintsUsed={hintsUsed}
            revealedHints={revealedHints}
            onUseHint={useHint}
          />
        )}

        {/* Checkpoint Progress */}
        {currentTask && (
          <CheckpointProgress
            checkpoints={currentTask.checkpoints}
            completedCheckpoints={completedCheckpoints}
          />
        )}

        {/* Next Task Button */}
        {currentTask && isTaskComplete(currentTask) &&
         currentTaskIndex < normalizedBlueprint.tasks.length - 1 && (
          <button
            onClick={nextTask}
            className="w-full bg-green-600 hover:bg-green-700 text-white font-semibold py-3 px-6 rounded-lg transition-colors shadow-md"
          >
            Continue to Next Task →
          </button>
        )}

        {/* Complete Button (last task) */}
        {currentTask && isTaskComplete(currentTask) &&
         currentTaskIndex === normalizedBlueprint.tasks.length - 1 && (
          <button
            onClick={nextTask}
            className="w-full bg-purple-600 hover:bg-purple-700 text-white font-semibold py-3 px-6 rounded-lg transition-colors shadow-md"
          >
            Complete Assessment ✓
          </button>
        )}
      </div>
    </div>
  );
}

// =============================================================================
// SUB-COMPONENTS
// =============================================================================

interface ScorePanelProps {
  score: number;
  maxScore: number;
  currentTask: number;
  totalTasks: number;
}

function ScorePanel({ score, maxScore, currentTask, totalTasks }: ScorePanelProps) {
  const percentage = maxScore > 0 ? Math.round((score / maxScore) * 100) : 0;

  return (
    <div className="bg-white rounded-lg shadow-md p-4">
      <div className="flex justify-between items-center mb-2">
        <span className="text-gray-600 font-medium">Score</span>
        <span className="text-2xl font-bold text-blue-600">{score}/{maxScore}</span>
      </div>
      <div className="w-full bg-gray-200 rounded-full h-2 mb-3">
        <div
          className="bg-blue-600 h-2 rounded-full transition-all duration-300"
          style={{ width: `${percentage}%` }}
        />
      </div>
      <div className="text-sm text-gray-500 text-center">
        Task {currentTask} of {totalTasks}
      </div>
    </div>
  );
}

interface TaskPanelProps {
  task: AssessmentTask;
  completedCheckpoints: Set<string>;
  hintsUsed: number;
  revealedHints: string[];
  onUseHint: () => void;
}

function TaskPanel({ task, completedCheckpoints, hintsUsed, revealedHints, onUseHint }: TaskPanelProps) {
  const hasMoreHints = task.hints && revealedHints.length < task.hints.length;

  return (
    <div className="bg-white rounded-lg shadow-md p-4">
      <div className="flex items-start justify-between mb-2">
        <h3 className="font-semibold text-gray-800">{task.title}</h3>
        <span className="px-2 py-1 bg-blue-100 text-blue-700 text-xs rounded-full capitalize">
          {task.type.replace('_', ' ')}
        </span>
      </div>

      <p className="text-gray-600 text-sm mb-4">{task.instructions}</p>

      {task.learningObjective && (
        <div className="mb-4 p-2 bg-green-50 rounded text-sm">
          <span className="font-medium text-green-700">Learning Goal: </span>
          <span className="text-green-600">{task.learningObjective}</span>
        </div>
      )}

      {/* Revealed Hints */}
      {revealedHints.length > 0 && (
        <div className="mb-4 space-y-2">
          {revealedHints.map((hint, index) => (
            <div key={index} className="p-2 bg-yellow-50 rounded border-l-4 border-yellow-400">
              <span className="text-yellow-800 text-sm">💡 {hint}</span>
            </div>
          ))}
        </div>
      )}

      {/* Hint Button */}
      {hasMoreHints && (
        <button
          onClick={onUseHint}
          className="text-sm text-blue-600 hover:text-blue-800 underline"
        >
          Need a hint? ({task.hints!.length - revealedHints.length} remaining)
        </button>
      )}

      {/* Prediction Question */}
      {task.prediction && (
        <div className="mt-4 p-3 bg-purple-50 rounded-lg">
          <p className="font-medium text-purple-800 mb-2">{task.prediction.question}</p>
          <div className="space-y-1">
            {task.prediction.options.map((option, index) => (
              <label key={index} className="flex items-center text-sm text-purple-700">
                <input type="radio" name="prediction" className="mr-2" />
                {option}
              </label>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

interface CheckpointProgressProps {
  checkpoints: Checkpoint[];
  completedCheckpoints: Set<string>;
}

function CheckpointProgress({ checkpoints, completedCheckpoints }: CheckpointProgressProps) {
  return (
    <div className="bg-white rounded-lg shadow-md p-4">
      <h4 className="font-medium text-gray-700 mb-3">Checkpoints</h4>
      <div className="space-y-2">
        {checkpoints.map((checkpoint) => {
          const isCompleted = completedCheckpoints.has(checkpoint.id);
          return (
            <div
              key={checkpoint.id}
              className={`flex items-center gap-3 p-2 rounded transition-colors ${
                isCompleted ? 'bg-green-50' : 'bg-gray-50'
              }`}
            >
              <div
                className={`w-6 h-6 rounded-full flex items-center justify-center flex-shrink-0 ${
                  isCompleted
                    ? 'bg-green-500 text-white'
                    : 'bg-gray-300 text-gray-500'
                }`}
              >
                {isCompleted ? '✓' : '○'}
              </div>
              <div className="flex-1 min-w-0">
                <p className={`text-sm ${isCompleted ? 'text-green-700' : 'text-gray-600'}`}>
                  {checkpoint.description}
                </p>
              </div>
              <div className="text-sm font-medium text-gray-500">
                {checkpoint.points}pts
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

interface ResultsPanelProps {
  score: number;
  maxScore: number;
  feedback: PhetSimulationBlueprint['feedback'];
  results: GameResults;
  onRestart: () => void;
}

function ResultsPanel({ score, maxScore, feedback, results, onRestart }: ResultsPanelProps) {
  const percentage = maxScore > 0 ? Math.round((score / maxScore) * 100) : 0;

  let feedbackKey: string;
  if (percentage >= 90) feedbackKey = 'perfect';
  else if (percentage >= 70) feedbackKey = 'good';
  else if (percentage >= 50) feedbackKey = 'passing';
  else feedbackKey = 'retry';

  const feedbackMessage = feedback.gameComplete[feedbackKey] || 'Great effort!';

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}m ${secs}s`;
  };

  return (
    <div className="min-h-[600px] flex items-center justify-center bg-gradient-to-b from-blue-50 to-white p-8">
      <div className="bg-white rounded-2xl shadow-xl p-8 max-w-md w-full text-center">
        {/* Score Circle */}
        <div className="relative w-32 h-32 mx-auto mb-6">
          <svg className="w-full h-full transform -rotate-90">
            <circle
              className="text-gray-200"
              strokeWidth="8"
              stroke="currentColor"
              fill="transparent"
              r="56"
              cx="64"
              cy="64"
            />
            <circle
              className="text-blue-600 transition-all duration-1000"
              strokeWidth="8"
              strokeDasharray={`${percentage * 3.51} 351`}
              strokeLinecap="round"
              stroke="currentColor"
              fill="transparent"
              r="56"
              cx="64"
              cy="64"
            />
          </svg>
          <div className="absolute inset-0 flex items-center justify-center">
            <span className="text-3xl font-bold text-gray-800">{percentage}%</span>
          </div>
        </div>

        {/* Score Text */}
        <p className="text-xl font-semibold text-gray-700 mb-2">
          {score} / {maxScore} points
        </p>

        {/* Feedback Message */}
        <p className="text-gray-600 mb-6">{feedbackMessage}</p>

        {/* Stats */}
        <div className="grid grid-cols-2 gap-4 mb-6 text-sm">
          <div className="bg-gray-50 rounded-lg p-3">
            <p className="text-gray-500">Time</p>
            <p className="font-semibold text-gray-700">{formatTime(results.timeSpentSeconds)}</p>
          </div>
          <div className="bg-gray-50 rounded-lg p-3">
            <p className="text-gray-500">Hints Used</p>
            <p className="font-semibold text-gray-700">{results.hintsUsed}</p>
          </div>
          <div className="bg-gray-50 rounded-lg p-3">
            <p className="text-gray-500">Checkpoints</p>
            <p className="font-semibold text-gray-700">{results.completedCheckpoints.length}</p>
          </div>
          <div className="bg-gray-50 rounded-lg p-3">
            <p className="text-gray-500">Tasks</p>
            <p className="font-semibold text-gray-700">{results.completedTasks.length}</p>
          </div>
        </div>

        {/* Restart Button */}
        <button
          onClick={onRestart}
          className="w-full bg-blue-600 hover:bg-blue-700 text-white font-semibold py-3 px-6 rounded-lg transition-colors"
        >
          Try Again
        </button>
      </div>
    </div>
  );
}

// =============================================================================
// HELPERS
// =============================================================================

function normalizeBlueprint(blueprint: any): PhetSimulationBlueprint {
  // Basic validation and normalization
  if (!blueprint) {
    throw new Error('Blueprint is required');
  }

  if (blueprint.templateType !== 'PHET_SIMULATION') {
    console.warn('Blueprint templateType is not PHET_SIMULATION');
  }

  // Ensure required fields have defaults
  return {
    templateType: 'PHET_SIMULATION',
    title: blueprint.title || 'PhET Simulation',
    narrativeIntro: blueprint.narrativeIntro || 'Explore this interactive simulation.',
    simulation: blueprint.simulation || { simulationId: 'projectile-motion', version: 'latest', parameters: [], interactions: [], outcomes: [] },
    assessmentType: blueprint.assessmentType || 'exploration',
    tasks: blueprint.tasks || [],
    scoring: blueprint.scoring || { maxScore: 100, hintPenalty: 2 },
    feedback: blueprint.feedback || {
      checkpointComplete: 'Great job!',
      taskComplete: 'Task completed!',
      incorrectAttempt: 'Try again!',
      hintUsed: "Here's a hint.",
      gameComplete: {
        perfect: 'Outstanding!',
        good: 'Well done!',
        passing: 'Good effort!',
        retry: 'Keep practicing!'
      }
    },
    animations: blueprint.animations || {
      checkpointComplete: { type: 'pulse', duration_ms: 400 },
      incorrectAttempt: { type: 'shake', duration_ms: 300 },
      taskComplete: { type: 'bounce', duration_ms: 500 },
      gameComplete: { type: 'confetti', duration_ms: 2000 }
    },
    learningObjectives: blueprint.learningObjectives || [],
    targetBloomsLevel: blueprint.targetBloomsLevel || 'understand',
    estimatedMinutes: blueprint.estimatedMinutes || 15,
    difficulty: blueprint.difficulty || 'medium',
    bridgeConfig: blueprint.bridgeConfig
  };
}

export default PhetSimulationGame;
