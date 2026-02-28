'use client';

import { useState, useCallback, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import dynamic from 'next/dynamic';
import ModeToggle from './components/ModeToggle';
import ScoreDisplay from './components/ScoreDisplay';
import { GameErrorBoundary } from './components/GameErrorBoundary';

// Lazy load individual game components
const StateTracerGame = dynamic(() => import('./StateTracerGame'), { ssr: false });
const BugHunterGame = dynamic(() => import('./BugHunterGame'), { ssr: false });
const AlgorithmBuilderGame = dynamic(() => import('./AlgorithmBuilderGame'), { ssr: false });
const ComplexityAnalyzerGame = dynamic(() => import('./ComplexityAnalyzerGame'), { ssr: false });
const ConstraintPuzzleGame = dynamic(() => import('./ConstraintPuzzleGame'), { ssr: false });

interface SceneBlueprint {
  scene_id: string;
  scene_number: number;
  title: string;
  game_type: string;
  difficulty: string;
  learning_goal: string;
  max_score: number;
  content: Record<string, unknown>;
  asset_url?: string | null;
}

interface MultiSceneBlueprint {
  templateType: string;
  title: string;
  algorithmName: string;
  narrativeIntro: string;
  totalMaxScore: number;
  is_multi_scene: boolean;
  scenes: SceneBlueprint[];
  scene_transitions?: Array<{ from_scene: string; to_scene: string; trigger: string }>;
  learn_config?: Record<string, unknown>;
  test_config?: Record<string, unknown>;
}

export interface AlgorithmMultiSceneGameProps {
  blueprint: MultiSceneBlueprint;
  onComplete?: (score: number) => void;
  theme?: 'dark' | 'light';
  gameplayMode?: 'learn' | 'test';
}

export default function AlgorithmMultiSceneGame({
  blueprint,
  onComplete,
  theme = 'dark',
  gameplayMode: initialMode = 'learn',
}: AlgorithmMultiSceneGameProps) {
  const isDark = theme === 'dark';
  const [currentSceneIndex, setCurrentSceneIndex] = useState(-1); // -1 = intro
  const [sceneScores, setSceneScores] = useState<Record<string, number>>({});
  const [gameplayMode, setGameplayMode] = useState<'learn' | 'test'>(initialMode);
  const [completed, setCompleted] = useState(false);
  const [retryKey, setRetryKey] = useState(0);

  const scenes = blueprint.scenes || [];
  const currentScene = currentSceneIndex >= 0 ? scenes[currentSceneIndex] : null;

  const totalScore = useMemo(
    () => Object.values(sceneScores).reduce((sum, s) => sum + s, 0),
    [sceneScores],
  );

  const handleSceneComplete = useCallback(
    (score: number) => {
      if (!currentScene) return;
      setSceneScores(prev => ({ ...prev, [currentScene.scene_id]: score }));

      // Advance to next scene or complete
      if (currentSceneIndex < scenes.length - 1) {
        setCurrentSceneIndex(prev => prev + 1);
      } else {
        setCompleted(true);
        onComplete?.(totalScore + score);
      }
    },
    [currentScene, currentSceneIndex, scenes.length, onComplete, totalScore],
  );

  const handleStart = useCallback(() => {
    setCurrentSceneIndex(0);
  }, []);

  const handleRestart = useCallback(() => {
    setCurrentSceneIndex(-1);
    setSceneScores({});
    setCompleted(false);
  }, []);

  // Skip the current scene (score 0) and advance — used by error boundary
  const handleSkipScene = useCallback(() => {
    handleSceneComplete(0);
  }, [handleSceneComplete]);

  // Increment retryKey to force remount of the crashed scene component
  const handleRetry = useCallback(() => {
    setRetryKey(k => k + 1);
  }, []);

  // Completion screen
  if (completed) {
    const pct = blueprint.totalMaxScore > 0
      ? Math.round((totalScore / blueprint.totalMaxScore) * 100)
      : 0;
    return (
      <div className={`rounded-xl p-8 text-center ${isDark ? 'bg-[#1a1a2e]' : 'bg-white'} shadow-xl`}>
        <div className="w-20 h-20 mx-auto mb-4 rounded-full bg-gradient-to-br from-blue-500 to-purple-500 flex items-center justify-center">
          <span className="text-3xl font-bold text-white">{pct}%</span>
        </div>
        <h2 className={`text-2xl font-bold mb-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          Game Complete!
        </h2>
        <p className={`text-lg mb-6 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          You scored {totalScore} out of {blueprint.totalMaxScore} points
        </p>
        <button
          onClick={handleRestart}
          className="px-6 py-3 bg-gradient-to-r from-blue-500 to-purple-500 text-white font-semibold rounded-lg hover:from-blue-600 hover:to-purple-600"
        >
          Play Again
        </button>
      </div>
    );
  }

  // Intro screen
  if (currentSceneIndex < 0) {
    return (
      <div className={`rounded-xl p-8 ${isDark ? 'bg-[#1a1a2e]' : 'bg-white'} shadow-xl`}>
        <div className="text-center max-w-2xl mx-auto">
          <h1 className={`text-3xl font-bold mb-3 ${isDark ? 'text-white' : 'text-gray-900'}`}>
            {blueprint.title}
          </h1>
          <p className={`text-lg mb-2 ${isDark ? 'text-blue-300' : 'text-blue-600'}`}>
            {blueprint.algorithmName}
          </p>
          <p className={`mb-6 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
            {blueprint.narrativeIntro}
          </p>

          {/* Scene overview */}
          <div className="grid gap-3 mb-8">
            {scenes.map((scene, i) => (
              <div
                key={scene.scene_id}
                className={`flex items-center gap-3 p-3 rounded-lg text-left ${
                  isDark ? 'bg-white/5' : 'bg-gray-50'
                }`}
              >
                <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold ${
                  isDark ? 'bg-blue-500/20 text-blue-300' : 'bg-blue-100 text-blue-700'
                }`}>
                  {i + 1}
                </div>
                <div className="flex-1">
                  <div className={`font-medium text-sm ${isDark ? 'text-white' : 'text-gray-900'}`}>
                    {scene.title}
                  </div>
                  <div className={`text-xs ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
                    {_gameTypeLabel(scene.game_type)} &middot; {scene.difficulty}
                  </div>
                </div>
                <div className={`text-xs ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>
                  {scene.max_score} pts
                </div>
              </div>
            ))}
          </div>

          <div className="flex items-center justify-center gap-4">
            <ModeToggle mode={gameplayMode} onToggle={setGameplayMode} />
            <button
              onClick={handleStart}
              className="px-6 py-3 bg-gradient-to-r from-blue-500 to-purple-500 text-white font-semibold rounded-lg hover:from-blue-600 hover:to-purple-600 transition-all shadow-lg"
            >
              Start Game
            </button>
          </div>
        </div>
      </div>
    );
  }

  // Scene rendering
  return (
    <div>
      {/* Scene progress bar */}
      <div className={`mb-4 rounded-lg p-3 ${isDark ? 'bg-[#1a1a2e]' : 'bg-white'} shadow`}>
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <span className={`text-sm font-medium ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
              Scene {currentSceneIndex + 1} of {scenes.length}
            </span>
            <span className={`text-xs px-2 py-0.5 rounded ${isDark ? 'bg-blue-500/20 text-blue-300' : 'bg-blue-100 text-blue-700'}`}>
              {currentScene?.title}
            </span>
          </div>
          <div className="flex items-center gap-3">
            <ModeToggle mode={gameplayMode} onToggle={setGameplayMode} disabled />
            <span className={`text-sm font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>
              {totalScore} pts
            </span>
          </div>
        </div>
        <div className={`h-1.5 rounded-full ${isDark ? 'bg-white/10' : 'bg-gray-200'}`}>
          <div
            className="h-full bg-gradient-to-r from-blue-500 to-purple-500 rounded-full transition-all"
            style={{ width: `${((currentSceneIndex + 1) / scenes.length) * 100}%` }}
          />
        </div>
      </div>

      {/* Scene game component */}
      <AnimatePresence mode="wait">
        <motion.div
          key={`${currentScene?.scene_id}-${retryKey}`}
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: -20 }}
          transition={{ duration: 0.3 }}
        >
          {currentScene && (
            <GameErrorBoundary
              sceneName={currentScene.title}
              gameType={currentScene.game_type}
              onSkipScene={handleSkipScene}
              onRetry={handleRetry}
            >
              {_renderScene(currentScene, handleSceneComplete, theme, gameplayMode)}
            </GameErrorBoundary>
          )}
        </motion.div>
      </AnimatePresence>
    </div>
  );
}

function _renderScene(
  scene: SceneBlueprint,
  onComplete: (score: number) => void,
  theme: 'dark' | 'light',
  gameplayMode: 'learn' | 'test' = 'learn',
) {
  const content = scene.content as Record<string, unknown>;
  const isDark = theme === 'dark';

  // Required field checks per game type to prevent crashes on incomplete LLM output
  const requiredFields: Record<string, string[]> = {
    state_tracer: ['steps', 'code'],
    bug_hunter: ['rounds'],
    algorithm_builder: ['correct_order'],
    complexity_analyzer: ['challenges'],
    constraint_puzzle: ['boardConfig', 'constraints'],
  };

  const required = requiredFields[scene.game_type] ?? [];
  const missing = required.filter((f) => !content[f]);
  if (missing.length > 0) {
    return (
      <div className={`rounded-xl p-8 text-center space-y-3 ${isDark ? 'bg-gray-800' : 'bg-gray-100'}`}>
        <div className="text-3xl">&#x26A0;&#xFE0F;</div>
        <p className={`font-medium ${isDark ? 'text-gray-200' : 'text-gray-800'}`}>
          This scene&apos;s content is incomplete
        </p>
        <p className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
          The AI didn&apos;t generate all required data for this {scene.game_type.replace(/_/g, ' ')} scene.
          Try regenerating the game.
        </p>
        <button
          onClick={() => onComplete(0)}
          className={`mt-2 px-4 py-2 rounded-lg text-sm font-medium ${isDark ? 'bg-gray-700 text-gray-200 hover:bg-gray-600' : 'bg-gray-200 text-gray-700 hover:bg-gray-300'}`}
        >
          Skip Scene
        </button>
      </div>
    );
  }

  switch (scene.game_type) {
    case 'state_tracer':
      return <StateTracerGame blueprint={content as never} onComplete={onComplete} theme={theme} gameplayMode={gameplayMode} />;
    case 'bug_hunter':
      return <BugHunterGame blueprint={content as never} onComplete={onComplete} theme={theme} gameplayMode={gameplayMode} />;
    case 'algorithm_builder':
      return <AlgorithmBuilderGame blueprint={content as never} onComplete={onComplete} theme={theme} gameplayMode={gameplayMode} />;
    case 'complexity_analyzer':
      return <ComplexityAnalyzerGame blueprint={content as never} onComplete={onComplete} theme={theme} gameplayMode={gameplayMode} />;
    case 'constraint_puzzle':
      return <ConstraintPuzzleGame blueprint={content as never} onComplete={onComplete} theme={theme} gameplayMode={gameplayMode} />;
    default:
      return (
        <div className="text-center py-8 text-muted-foreground">
          Unknown game type: {scene.game_type}
        </div>
      );
  }
}

function _gameTypeLabel(gameType: string): string {
  const labels: Record<string, string> = {
    state_tracer: 'State Tracer',
    bug_hunter: 'Bug Hunter',
    algorithm_builder: 'Algorithm Builder',
    complexity_analyzer: 'Complexity Analyzer',
    constraint_puzzle: 'Constraint Puzzle',
  };
  return labels[gameType] || gameType;
}
