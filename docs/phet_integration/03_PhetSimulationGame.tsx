/**
 * PhET Simulation Game Component
 *
 * This React component renders PhET simulations within the GamED.AI game player.
 * It handles PhET-iO wrapper communication, state synchronization, and scoring integration.
 *
 * Integration Point: Add to frontend/src/components/templates/PhetSimulationGame/
 */

import React, {
  useEffect,
  useRef,
  useState,
  useCallback,
  useMemo,
} from "react";

// Types
interface PhetCheckpoint {
  id: string;
  description: string;
  phetioID: string;
  expectedValue?: any;
  expectedRange?: { min: number; max: number };
  points: number;
}

interface PhetTask {
  id: string;
  questionText: string;
  interactionType: string;
  instructions?: string;
  hints?: string[];
  checkpoints: PhetCheckpoint[];
  requiredToProceed: boolean;
}

interface PhetCustomization {
  launchParams?: {
    phetioEmitStates?: boolean;
    phetioEmitDeltas?: boolean;
    screen?: string;
  };
  initialStates?: Array<{ phetioID: string; value: any }>;
  hiddenElements?: string[];
}

interface PhetBlueprint {
  templateType: "PHET_SIMULATION";
  title: string;
  narrativeIntro: string;
  simulationId: string;
  simulationVersion: string;
  customization?: PhetCustomization;
  tasks: PhetTask[];
  animationCues: {
    taskStart: string;
    checkpointReached: string;
    taskComplete: string;
    incorrectAttempt: string;
  };
  learningObjectives?: string[];
  estimatedDurationMinutes?: number;
}

interface PhetSimulationGameProps {
  blueprint: PhetBlueprint;
  onComplete?: (results: GameResults) => void;
  onProgress?: (progress: GameProgress) => void;
}

interface GameProgress {
  currentTaskIndex: number;
  totalTasks: number;
  completedCheckpoints: string[];
  score: number;
  maxScore: number;
}

interface GameResults {
  finalScore: number;
  maxScore: number;
  completedTasks: string[];
  timeSpentSeconds: number;
  interactionCount: number;
  checkpointResults: Array<{
    checkpointId: string;
    achieved: boolean;
    points: number;
  }>;
}

interface SimulationState {
  isLoaded: boolean;
  isInitialized: boolean;
  currentValues: Record<string, any>;
}

// PhET Base URL
const PHET_BASE_URL = "https://phet.colorado.edu/sims/html";

/**
 * Build the PhET simulation URL with parameters
 */
function buildSimulationUrl(
  simulationId: string,
  version: string,
  launchParams?: PhetCustomization["launchParams"]
): string {
  const baseUrl = `${PHET_BASE_URL}/${simulationId}/${version}/${simulationId}_all.html`;
  const params = new URLSearchParams();

  // Always enable PhET-iO mode
  params.append("brand", "phet-io");

  // Add launch parameters
  if (launchParams) {
    if (launchParams.phetioEmitStates) {
      params.append("phetioEmitStates", "true");
    }
    if (launchParams.phetioEmitDeltas) {
      params.append("phetioEmitDeltas", "true");
    }
    if (launchParams.screen) {
      params.append("screens", launchParams.screen);
    }
  }

  return `${baseUrl}?${params.toString()}`;
}

/**
 * PhET Bridge Service - Handles communication with PhET-iO simulation
 */
class PhetBridgeService {
  private iframe: HTMLIFrameElement;
  private messageHandlers: Map<string, (data: any) => void> = new Map();
  private stateCache: Record<string, any> = {};

  constructor(iframe: HTMLIFrameElement) {
    this.iframe = iframe;
    this.setupMessageListener();
  }

  private setupMessageListener() {
    window.addEventListener("message", this.handleMessage.bind(this));
  }

  private handleMessage(event: MessageEvent) {
    // Validate origin (in production, check against PhET domains)
    if (!event.data || typeof event.data !== "object") return;

    const { type, phetioID, data, method } = event.data;

    // Update state cache for property changes
    if (type === "propertyValueChange" && phetioID) {
      this.stateCache[phetioID] = data?.newValue;
    }

    // Notify handlers
    const handler = this.messageHandlers.get(type);
    if (handler) {
      handler({ type, phetioID, data, method });
    }

    // Also notify wildcard handlers
    const wildcardHandler = this.messageHandlers.get("*");
    if (wildcardHandler) {
      wildcardHandler({ type, phetioID, data, method });
    }
  }

  /**
   * Subscribe to PhET-iO events
   */
  onEvent(eventType: string, handler: (data: any) => void) {
    this.messageHandlers.set(eventType, handler);
    return () => this.messageHandlers.delete(eventType);
  }

  /**
   * Invoke a method on a PhET-iO element
   */
  invoke(phetioID: string, methodName: string, args: any[] = []) {
    this.iframe.contentWindow?.postMessage(
      {
        type: "invoke",
        phetioID,
        method: methodName,
        args,
      },
      "*"
    );
  }

  /**
   * Set a property value
   */
  setValue(phetioID: string, value: any) {
    this.invoke(phetioID, "setValue", [value]);
  }

  /**
   * Get current cached value for a phetioID
   */
  getValue(phetioID: string): any {
    return this.stateCache[phetioID];
  }

  /**
   * Get full state cache
   */
  getState(): Record<string, any> {
    return { ...this.stateCache };
  }

  /**
   * Request state update from simulation
   */
  requestState() {
    this.iframe.contentWindow?.postMessage({ type: "getState" }, "*");
  }

  /**
   * Cleanup
   */
  destroy() {
    window.removeEventListener("message", this.handleMessage.bind(this));
    this.messageHandlers.clear();
  }
}

/**
 * Custom hook for PhET simulation state management
 */
function usePhetSimulation(blueprint: PhetBlueprint) {
  const iframeRef = useRef<HTMLIFrameElement>(null);
  const bridgeRef = useRef<PhetBridgeService | null>(null);

  const [simState, setSimState] = useState<SimulationState>({
    isLoaded: false,
    isInitialized: false,
    currentValues: {},
  });

  const [currentTaskIndex, setCurrentTaskIndex] = useState(0);
  const [completedCheckpoints, setCompletedCheckpoints] = useState<Set<string>>(
    new Set()
  );
  const [score, setScore] = useState(0);
  const [interactionCount, setInteractionCount] = useState(0);
  const [hintsUsed, setHintsUsed] = useState(0);

  // Calculate max score
  const maxScore = useMemo(() => {
    return blueprint.tasks.reduce((total, task) => {
      return (
        total + task.checkpoints.reduce((sum, cp) => sum + cp.points, 0)
      );
    }, 0);
  }, [blueprint]);

  // Initialize bridge when iframe loads
  useEffect(() => {
    const iframe = iframeRef.current;
    if (!iframe) return;

    const handleLoad = () => {
      bridgeRef.current = new PhetBridgeService(iframe);
      setSimState((prev) => ({ ...prev, isLoaded: true }));

      // Apply initial states from customization
      if (blueprint.customization?.initialStates) {
        blueprint.customization.initialStates.forEach(({ phetioID, value }) => {
          bridgeRef.current?.setValue(phetioID, value);
        });
      }

      // Subscribe to property changes
      bridgeRef.current.onEvent("propertyValueChange", handlePropertyChange);
      bridgeRef.current.onEvent("simInitialized", () => {
        setSimState((prev) => ({ ...prev, isInitialized: true }));
      });
    };

    iframe.addEventListener("load", handleLoad);
    return () => {
      iframe.removeEventListener("load", handleLoad);
      bridgeRef.current?.destroy();
    };
  }, [blueprint]);

  // Handle property changes and check for checkpoint completion
  const handlePropertyChange = useCallback(
    (eventData: { phetioID: string; data: { newValue: any } }) => {
      const { phetioID, data } = eventData;

      // Update state
      setSimState((prev) => ({
        ...prev,
        currentValues: {
          ...prev.currentValues,
          [phetioID]: data.newValue,
        },
      }));

      // Increment interaction count
      setInteractionCount((prev) => prev + 1);

      // Check if any checkpoint is satisfied
      const currentTask = blueprint.tasks[currentTaskIndex];
      if (!currentTask) return;

      currentTask.checkpoints.forEach((checkpoint) => {
        if (completedCheckpoints.has(checkpoint.id)) return;

        if (checkpoint.phetioID === phetioID) {
          let satisfied = false;

          if (checkpoint.expectedValue !== undefined) {
            satisfied = data.newValue === checkpoint.expectedValue;
          } else if (checkpoint.expectedRange) {
            satisfied =
              data.newValue >= checkpoint.expectedRange.min &&
              data.newValue <= checkpoint.expectedRange.max;
          }

          if (satisfied) {
            setCompletedCheckpoints((prev) => new Set([...prev, checkpoint.id]));
            setScore((prev) => prev + checkpoint.points);
          }
        }
      });
    },
    [blueprint, currentTaskIndex, completedCheckpoints]
  );

  // Check if current task is complete
  const isCurrentTaskComplete = useMemo(() => {
    const currentTask = blueprint.tasks[currentTaskIndex];
    if (!currentTask) return false;

    return currentTask.checkpoints.every((cp) =>
      completedCheckpoints.has(cp.id)
    );
  }, [blueprint, currentTaskIndex, completedCheckpoints]);

  // Move to next task
  const goToNextTask = useCallback(() => {
    if (currentTaskIndex < blueprint.tasks.length - 1) {
      setCurrentTaskIndex((prev) => prev + 1);
    }
  }, [currentTaskIndex, blueprint.tasks.length]);

  // Use hint
  const useHint = useCallback(() => {
    setHintsUsed((prev) => prev + 1);
  }, []);

  // Build simulation URL
  const simulationUrl = useMemo(() => {
    return buildSimulationUrl(
      blueprint.simulationId,
      blueprint.simulationVersion,
      blueprint.customization?.launchParams
    );
  }, [blueprint]);

  return {
    iframeRef,
    simState,
    simulationUrl,
    currentTaskIndex,
    currentTask: blueprint.tasks[currentTaskIndex],
    completedCheckpoints,
    isCurrentTaskComplete,
    score,
    maxScore,
    interactionCount,
    hintsUsed,
    goToNextTask,
    useHint,
  };
}

/**
 * Task Panel Component
 */
const TaskPanel: React.FC<{
  task: PhetTask;
  completedCheckpoints: Set<string>;
  onUseHint: () => void;
  hintsUsed: number;
}> = ({ task, completedCheckpoints, onUseHint, hintsUsed }) => {
  const [showHint, setShowHint] = useState(false);

  const availableHints = task.hints || [];
  const currentHintIndex = Math.min(hintsUsed, availableHints.length - 1);

  return (
    <div className="bg-white rounded-lg shadow-md p-4 mb-4">
      <h3 className="text-lg font-semibold text-gray-800 mb-2">
        {task.questionText}
      </h3>

      {task.instructions && (
        <p className="text-gray-600 text-sm mb-3">{task.instructions}</p>
      )}

      {/* Checkpoints */}
      <div className="space-y-2 mb-4">
        <h4 className="text-sm font-medium text-gray-700">Progress:</h4>
        {task.checkpoints.map((checkpoint) => (
          <div
            key={checkpoint.id}
            className={`flex items-center gap-2 text-sm ${
              completedCheckpoints.has(checkpoint.id)
                ? "text-green-600"
                : "text-gray-500"
            }`}
          >
            <span
              className={`w-5 h-5 rounded-full flex items-center justify-center text-xs ${
                completedCheckpoints.has(checkpoint.id)
                  ? "bg-green-100"
                  : "bg-gray-100"
              }`}
            >
              {completedCheckpoints.has(checkpoint.id) ? "✓" : "○"}
            </span>
            <span>{checkpoint.description}</span>
            <span className="ml-auto text-xs">
              {checkpoint.points} pts
            </span>
          </div>
        ))}
      </div>

      {/* Hint Button */}
      {availableHints.length > 0 && (
        <div>
          <button
            onClick={() => {
              setShowHint(true);
              onUseHint();
            }}
            className="text-blue-600 text-sm hover:underline"
            disabled={hintsUsed >= availableHints.length}
          >
            {showHint
              ? `Hint ${hintsUsed} of ${availableHints.length}`
              : "Need a hint?"}
          </button>
          {showHint && hintsUsed <= availableHints.length && (
            <p className="mt-2 text-sm text-blue-700 bg-blue-50 p-2 rounded">
              💡 {availableHints[currentHintIndex]}
            </p>
          )}
        </div>
      )}
    </div>
  );
};

/**
 * Score Panel Component
 */
const ScorePanel: React.FC<{
  score: number;
  maxScore: number;
  currentTaskIndex: number;
  totalTasks: number;
}> = ({ score, maxScore, currentTaskIndex, totalTasks }) => {
  const percentage = maxScore > 0 ? Math.round((score / maxScore) * 100) : 0;

  return (
    <div className="bg-gradient-to-r from-purple-500 to-indigo-600 text-white rounded-lg p-4 mb-4">
      <div className="flex justify-between items-center mb-2">
        <span className="text-sm opacity-90">Score</span>
        <span className="text-2xl font-bold">
          {score} / {maxScore}
        </span>
      </div>
      <div className="w-full bg-white/30 rounded-full h-2 mb-2">
        <div
          className="bg-white rounded-full h-2 transition-all duration-500"
          style={{ width: `${percentage}%` }}
        />
      </div>
      <div className="text-sm opacity-90">
        Task {currentTaskIndex + 1} of {totalTasks}
      </div>
    </div>
  );
};

/**
 * Main PhET Simulation Game Component
 */
export const PhetSimulationGame: React.FC<PhetSimulationGameProps> = ({
  blueprint,
  onComplete,
  onProgress,
}) => {
  const {
    iframeRef,
    simState,
    simulationUrl,
    currentTaskIndex,
    currentTask,
    completedCheckpoints,
    isCurrentTaskComplete,
    score,
    maxScore,
    interactionCount,
    hintsUsed,
    goToNextTask,
    useHint,
  } = usePhetSimulation(blueprint);

  const [startTime] = useState(Date.now());
  const [showResults, setShowResults] = useState(false);

  // Report progress
  useEffect(() => {
    onProgress?.({
      currentTaskIndex,
      totalTasks: blueprint.tasks.length,
      completedCheckpoints: Array.from(completedCheckpoints),
      score,
      maxScore,
    });
  }, [currentTaskIndex, completedCheckpoints, score, maxScore, onProgress]);

  // Handle task completion
  useEffect(() => {
    if (isCurrentTaskComplete) {
      // Check if this was the last task
      if (currentTaskIndex === blueprint.tasks.length - 1) {
        // All tasks complete
        const results: GameResults = {
          finalScore: score,
          maxScore,
          completedTasks: blueprint.tasks.map((t) => t.id),
          timeSpentSeconds: Math.floor((Date.now() - startTime) / 1000),
          interactionCount,
          checkpointResults: blueprint.tasks.flatMap((task) =>
            task.checkpoints.map((cp) => ({
              checkpointId: cp.id,
              achieved: completedCheckpoints.has(cp.id),
              points: completedCheckpoints.has(cp.id) ? cp.points : 0,
            }))
          ),
        };
        setShowResults(true);
        onComplete?.(results);
      }
    }
  }, [isCurrentTaskComplete, currentTaskIndex, blueprint.tasks, score, maxScore, startTime, interactionCount, completedCheckpoints, onComplete]);

  // Results screen
  if (showResults) {
    return (
      <div className="max-w-2xl mx-auto p-8 text-center">
        <div className="bg-gradient-to-br from-green-400 to-blue-500 text-white rounded-2xl p-8 mb-6">
          <h2 className="text-3xl font-bold mb-4">🎉 Simulation Complete!</h2>
          <div className="text-6xl font-bold mb-2">{score}</div>
          <div className="text-xl opacity-90">out of {maxScore} points</div>
        </div>
        <div className="bg-white rounded-lg shadow-md p-6">
          <h3 className="font-semibold mb-4">Session Summary</h3>
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div className="bg-gray-50 p-3 rounded">
              <div className="text-gray-500">Time Spent</div>
              <div className="font-semibold">
                {Math.floor((Date.now() - startTime) / 60000)} min
              </div>
            </div>
            <div className="bg-gray-50 p-3 rounded">
              <div className="text-gray-500">Interactions</div>
              <div className="font-semibold">{interactionCount}</div>
            </div>
            <div className="bg-gray-50 p-3 rounded">
              <div className="text-gray-500">Hints Used</div>
              <div className="font-semibold">{hintsUsed}</div>
            </div>
            <div className="bg-gray-50 p-3 rounded">
              <div className="text-gray-500">Checkpoints</div>
              <div className="font-semibold">
                {completedCheckpoints.size} /{" "}
                {blueprint.tasks.flatMap((t) => t.checkpoints).length}
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col lg:flex-row gap-4 p-4 bg-gray-100">
      {/* Simulation Panel */}
      <div className="flex-1 flex flex-col">
        <div className="bg-white rounded-lg shadow-md overflow-hidden flex-1">
          {!simState.isLoaded && (
            <div className="absolute inset-0 flex items-center justify-center bg-gray-100">
              <div className="text-center">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4" />
                <p className="text-gray-600">Loading PhET Simulation...</p>
              </div>
            </div>
          )}
          <iframe
            ref={iframeRef}
            src={simulationUrl}
            className="w-full h-full min-h-[500px]"
            title={blueprint.title}
            allow="fullscreen"
            sandbox="allow-scripts allow-same-origin"
          />
        </div>
      </div>

      {/* Task & Score Panel */}
      <div className="w-full lg:w-80 flex flex-col">
        <ScorePanel
          score={score}
          maxScore={maxScore}
          currentTaskIndex={currentTaskIndex}
          totalTasks={blueprint.tasks.length}
        />

        {currentTask && (
          <TaskPanel
            task={currentTask}
            completedCheckpoints={completedCheckpoints}
            onUseHint={useHint}
            hintsUsed={hintsUsed}
          />
        )}

        {/* Next Task Button */}
        {isCurrentTaskComplete &&
          currentTaskIndex < blueprint.tasks.length - 1 && (
            <button
              onClick={goToNextTask}
              className="w-full bg-green-600 hover:bg-green-700 text-white font-semibold py-3 px-6 rounded-lg transition-colors"
            >
              Continue to Next Task →
            </button>
          )}

        {/* Narrative Intro */}
        <div className="mt-4 p-4 bg-blue-50 rounded-lg text-sm text-blue-800">
          <h4 className="font-semibold mb-1">{blueprint.title}</h4>
          <p>{blueprint.narrativeIntro}</p>
        </div>
      </div>
    </div>
  );
};

export default PhetSimulationGame;
