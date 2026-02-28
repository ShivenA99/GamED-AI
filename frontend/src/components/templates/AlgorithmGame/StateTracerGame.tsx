'use client';

import { useCallback, useEffect, useMemo, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import CodeDisplay from '../CodeDisplay';
import VariableTracker from '../VariableTracker';
import StepControls from '../StepControls';
import DataStructureVisualizer from './components/DataStructureVisualizer';
import ScoreDisplay from './components/ScoreDisplay';
import PredictionPanel from './components/PredictionPanel';
import DiffOverlay from './components/DiffOverlay';
import HintSystem from './components/HintSystem';
import CompletionScreen from './components/CompletionScreen';
import { useStateTracerMachine } from './hooks/useStateTracerMachine';
import { useScoring } from './hooks/useScoring';
import {
  StateTracerBlueprint,
  PredictionResult,
  DEFAULT_SCORING,
  GameplayMode,
  ExtendedPrediction,
  CodeCompletionPrediction,
  TrueFalsePrediction,
} from './types';

interface StateTracerGameProps {
  blueprint: StateTracerBlueprint;
  onComplete?: (score: number) => void;
  theme?: 'dark' | 'light';
  gameplayMode?: GameplayMode;
}

export default function StateTracerGame({
  blueprint,
  onComplete,
  theme = 'dark',
  gameplayMode = 'learn',
}: StateTracerGameProps) {
  const isTestMode = gameplayMode === 'test';
  const hintPenalties: [number, number, number] = isTestMode ? [0.1, 0.2, 0.3] : [0, 0, 0];
  const config = blueprint.scoringConfig || DEFAULT_SCORING;
  const { state, dispatch, goToStep, advanceToNext, reset, currentStep } =
    useStateTracerMachine(blueprint.steps);
  const { scoreStep, computeFinalScore, getStreakMultiplier } = useScoring(config);

  const multiplier = getStreakMultiplier(state.scoring.streak);

  // Previous variables for VariableTracker change detection
  const prevStepIndex = Math.max(0, state.currentStepIndex - 1);
  const prevStep = blueprint.steps[prevStepIndex];
  const previousVariables = prevStep?.variables || {};

  // Compute executed code lines from all visited steps
  const executedLines = useMemo(() => {
    const lines = new Set<number>();
    for (let i = 0; i <= state.currentStepIndex; i++) {
      lines.add(blueprint.steps[i].codeLine);
    }
    return [...lines];
  }, [state.currentStepIndex, blueprint.steps]);

  // Start the game on mount
  useEffect(() => {
    if (state.phase === 'INIT') {
      goToStep(0);
    }
  }, [state.phase, goToStep]);

  // Handle prediction submission
  const handlePredictionSubmit = useCallback(
    (answer: number[] | string | string[] | boolean) => {
      if (!currentStep?.prediction) return;
      const pred = currentStep.prediction;

      let isCorrect = false;
      let correctAnswer: number[] | string | string[] = '';

      switch (pred.type) {
        case 'arrangement': {
          const playerArr = answer as number[];
          isCorrect =
            playerArr.length === pred.correctArrangement.length &&
            playerArr.every((v, i) => v === pred.correctArrangement[i]);
          correctAnswer = pred.correctArrangement;
          break;
        }
        case 'value': {
          const playerStr = (answer as string).toLowerCase().trim();
          const acceptable = pred.acceptableValues
            ? pred.acceptableValues.map((v) => v.toLowerCase().trim())
            : [pred.correctValue.toLowerCase().trim()];
          isCorrect = acceptable.includes(playerStr);
          correctAnswer = pred.correctValue;
          break;
        }
        case 'multiple_choice': {
          isCorrect = answer === pred.correctId;
          correctAnswer = pred.correctId;
          break;
        }
        case 'multi_select': {
          const selected = answer as string[];
          const correct = new Set(pred.correctIds);
          isCorrect =
            selected.length === correct.size &&
            selected.every((s) => correct.has(s));
          correctAnswer = pred.correctIds;
          break;
        }
        case 'code_completion': {
          const playerCode = (answer as string).trim();
          const ccPred = pred as CodeCompletionPrediction;
          isCorrect =
            playerCode === ccPred.correctCode.trim() ||
            (ccPred.acceptableVariants ?? []).some((v: string) => playerCode === v.trim());
          correctAnswer = ccPred.correctCode;
          break;
        }
        case 'true_false': {
          const tfPred = pred as TrueFalsePrediction;
          isCorrect = answer === tfPred.correctAnswer;
          correctAnswer = String(tfPred.correctAnswer);
          break;
        }
      }

      // Normalize boolean answers to strings for PredictionResult compatibility
      const normalizedAnswer: number[] | string | string[] =
        typeof answer === 'boolean' ? String(answer) : answer;

      const result: PredictionResult = {
        isCorrect,
        partialScore: 0,
        playerAnswer: normalizedAnswer,
        correctAnswer,
      };

      const { points } = scoreStep(
        pred,
        result,
        state.scoring.streak,
        state.hintState.currentTier,
      );
      result.partialScore = points / config.basePoints;

      dispatch({ type: 'SUBMIT_PREDICTION', result, pointsEarned: points });

      // Auto-advance after showing result
      setTimeout(() => {
        dispatch({ type: 'FINISH_REVEAL' });
      }, 300);
    },
    [currentStep, scoreStep, state.scoring.streak, state.hintState.currentTier, config.basePoints, dispatch],
  );

  // Handle advancing after reveal
  const handleAdvanceAfterReveal = useCallback(() => {
    advanceToNext();
  }, [advanceToNext]);

  // Handle hint request
  const handleHintRequest = useCallback(
    (tier: number) => {
      dispatch({ type: 'USE_HINT', tier });
    },
    [dispatch],
  );

  // Handle step controls
  const handlePrev = useCallback(() => {
    if (state.currentStepIndex > 0) {
      goToStep(state.currentStepIndex - 1);
    }
  }, [state.currentStepIndex, goToStep]);

  const handleNext = useCallback(() => {
    // If awaiting prediction, don't allow skip
    if (state.phase === 'AWAITING_PREDICTION') return;
    // If showing result, advance
    if (state.phase === 'REVEALING_RESULT' || state.phase === 'PREDICTION_SUBMITTED') {
      handleAdvanceAfterReveal();
      return;
    }
    advanceToNext();
  }, [state.phase, advanceToNext, handleAdvanceAfterReveal]);

  const handleReset = useCallback(() => {
    reset();
    setTimeout(() => goToStep(0), 50);
  }, [reset, goToStep]);

  // Final score computation
  const finalScore = computeFinalScore(state.scoring);

  // Fire onComplete exactly once when game completes (must be in useEffect, not render body)
  const completedRef = useRef(false);
  useEffect(() => {
    if (state.phase === 'COMPLETED' && !completedRef.current) {
      completedRef.current = true;
      onComplete?.(finalScore);
    }
  }, [state.phase, finalScore, onComplete]);

  // Reset the ref when game is reset
  useEffect(() => {
    if (state.phase === 'INIT') {
      completedRef.current = false;
    }
  }, [state.phase]);

  // Completion
  if (state.phase === 'COMPLETED') {
    return (
      <CompletionScreen
        scoring={state.scoring}
        finalScore={finalScore}
        totalSteps={blueprint.steps.filter((s) => s.prediction !== null).length}
        onReset={handleReset}
        theme={theme}
      />
    );
  }

  const isBlocked =
    state.phase === 'AWAITING_PREDICTION' ||
    state.phase === 'PREDICTION_SUBMITTED';

  return (
    <div
      className={`rounded-xl overflow-hidden ${
        theme === 'dark' ? 'bg-gray-900' : 'bg-white'
      }`}
    >
      {/* Header */}
      <div
        className={`px-6 py-4 border-b ${
          theme === 'dark' ? 'border-gray-700 bg-gray-800' : 'border-gray-200 bg-gray-50'
        }`}
      >
        <h2
          className={`text-xl font-bold ${
            theme === 'dark' ? 'text-white' : 'text-gray-900'
          }`}
        >
          {blueprint.algorithmName}
        </h2>
        <p
          className={`text-sm mt-1 ${
            theme === 'dark' ? 'text-gray-400' : 'text-gray-600'
          }`}
        >
          {blueprint.narrativeIntro}
        </p>
      </div>

      {/* Score bar */}
      <div className="px-6 py-2">
        <ScoreDisplay
          scoring={state.scoring}
          multiplier={multiplier}
          theme={theme}
        />
      </div>

      {/* Main content */}
      <div className="p-6">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left 2/3: Code + Data Structure + Prediction */}
          <div className="lg:col-span-2 space-y-4">
            <CodeDisplay
              code={blueprint.code}
              language={blueprint.language}
              currentLine={currentStep?.codeLine || 1}
              executedLines={executedLines}
              theme={theme}
            />

            {/* Step description */}
            {currentStep && (
              <motion.div
                key={state.currentStepIndex}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                className={`p-4 rounded-lg ${
                  theme === 'dark' ? 'bg-gray-800' : 'bg-gray-100'
                }`}
              >
                <div className="flex items-start">
                  <div className="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 mr-3 bg-gradient-to-br from-primary-500 to-secondary-500 text-white font-bold text-sm">
                    {currentStep.stepNumber}
                  </div>
                  <div>
                    <p
                      className={`font-medium ${
                        theme === 'dark' ? 'text-white' : 'text-gray-900'
                      }`}
                    >
                      Line {currentStep.codeLine}
                    </p>
                    <p
                      className={`mt-1 text-sm ${
                        theme === 'dark' ? 'text-gray-300' : 'text-gray-600'
                      }`}
                    >
                      {currentStep.description}
                    </p>
                  </div>
                </div>
              </motion.div>
            )}

            {/* Data Structure Visualizer */}
            {currentStep && (
              <DataStructureVisualizer
                dataStructure={currentStep.dataStructure}
                theme={theme}
              />
            )}

            {/* Prediction Panel */}
            <AnimatePresence mode="wait">
              {state.phase === 'AWAITING_PREDICTION' && currentStep?.prediction && (
                <PredictionPanel
                  key={`pred-${state.currentStepIndex}`}
                  prediction={currentStep.prediction}
                  onSubmit={handlePredictionSubmit}
                  disabled={false}
                  theme={theme}
                />
              )}

              {(state.phase === 'PREDICTION_SUBMITTED' ||
                state.phase === 'REVEALING_RESULT') &&
                currentStep?.prediction &&
                state.lastResult && (
                  <motion.div
                    key={`result-${state.currentStepIndex}`}
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    className="space-y-3"
                  >
                    <DiffOverlay
                      prediction={currentStep.prediction}
                      result={state.lastResult}
                      theme={theme}
                    />

                    {/* Explanation — shown in learn mode or when correct */}
                    {(!isTestMode || state.lastResult.isCorrect) && (
                    <div
                      className={`p-3 rounded-lg text-sm ${
                        theme === 'dark'
                          ? 'bg-gray-800 text-gray-300'
                          : 'bg-gray-100 text-gray-600'
                      }`}
                    >
                      {currentStep.explanation}
                    </div>
                    )}

                    {/* Points earned */}
                    <AnimatePresence>
                      {state.scoring.stepScores.length > 0 && (
                        <motion.div
                          initial={{ opacity: 0, y: -10 }}
                          animate={{ opacity: 1, y: 0 }}
                          className="text-center"
                        >
                          <span
                            className={`text-lg font-bold ${
                              state.lastResult.isCorrect
                                ? 'text-green-400'
                                : 'text-gray-500'
                            }`}
                          >
                            +{state.scoring.stepScores[state.scoring.stepScores.length - 1]}
                          </span>
                        </motion.div>
                      )}
                    </AnimatePresence>

                    {/* Continue button */}
                    <div className="flex justify-center">
                      <motion.button
                        whileHover={{ scale: 1.02 }}
                        whileTap={{ scale: 0.98 }}
                        onClick={handleAdvanceAfterReveal}
                        className="px-6 py-2 rounded-lg font-medium text-sm bg-primary-500 text-white hover:bg-primary-600 transition-colors"
                      >
                        Continue
                      </motion.button>
                    </div>
                  </motion.div>
                )}
            </AnimatePresence>

            {/* Hints (only during prediction) */}
            {state.phase === 'AWAITING_PREDICTION' && currentStep?.hints && (
              <HintSystem
                hints={currentStep.hints}
                currentTier={state.hintState.currentTier}
                onRequestHint={handleHintRequest}
                theme={theme}
                hintPenalties={hintPenalties}
              />
            )}
          </div>

          {/* Right 1/3: Variables */}
          <div className="space-y-4">
            {currentStep && (
              <VariableTracker
                variables={currentStep.variables}
                previousVariables={previousVariables}
                highlightChanges={true}
                showHistory={true}
                theme={theme}
              />
            )}
          </div>
        </div>

        {/* Step controls */}
        <div className="mt-6">
          <StepControls
            currentStep={state.currentStepIndex}
            totalSteps={blueprint.steps.length}
            isPlaying={state.isPlaying}
            speed={state.speed}
            onPrev={handlePrev}
            onNext={handleNext}
            onPlay={() => dispatch({ type: 'SET_PLAYING', isPlaying: true })}
            onPause={() => dispatch({ type: 'SET_PLAYING', isPlaying: false })}
            onReset={handleReset}
            onSpeedChange={(s) => dispatch({ type: 'SET_SPEED', speed: s })}
            disabled={isBlocked}
            theme={theme}
          />
        </div>
      </div>
    </div>
  );
}
