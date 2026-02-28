'use client';

import { useMemo, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import Link from 'next/link';
import dynamic from 'next/dynamic';
import { ACL_GAMES } from '@/data/acl-demo';
import {
  DOMAIN_LABELS,
  DOMAIN_ICONS,
  LEVEL_LABELS,
  MECHANIC_LABELS,
} from '@/data/acl-demo/types';
import type { ACLGameEntry } from '@/data/acl-demo/types';
import ModeToggle from '@/components/templates/AlgorithmGame/components/ModeToggle';
import { ThemeToggle } from '@/components/ui/ThemeToggle';

// Lazy load game components
const InteractiveDiagramGame = dynamic(
  () => import('@/components/templates/InteractiveDiagramGame'),
  { ssr: false, loading: () => <GameSkeleton /> }
);

const StateTracerGame = dynamic(
  () => import('@/components/templates/AlgorithmGame/StateTracerGame'),
  { ssr: false, loading: () => <GameSkeleton /> }
);

const BugHunterGame = dynamic(
  () => import('@/components/templates/AlgorithmGame/BugHunterGame'),
  { ssr: false, loading: () => <GameSkeleton /> }
);

const AlgorithmBuilderGame = dynamic(
  () => import('@/components/templates/AlgorithmGame/AlgorithmBuilderGame'),
  { ssr: false, loading: () => <GameSkeleton /> }
);

const ComplexityAnalyzerGame = dynamic(
  () => import('@/components/templates/AlgorithmGame/ComplexityAnalyzerGame'),
  { ssr: false, loading: () => <GameSkeleton /> }
);

const ConstraintPuzzleGame = dynamic(
  () => import('@/components/templates/AlgorithmGame/ConstraintPuzzleGame'),
  { ssr: false, loading: () => <GameSkeleton /> }
);

const AlgorithmMultiSceneGame = dynamic(
  () => import('@/components/templates/AlgorithmGame/AlgorithmMultiSceneGame'),
  { ssr: false, loading: () => <GameSkeleton /> }
);

function GameSkeleton() {
  return (
    <div className="animate-pulse space-y-4 p-8">
      <div className="h-8 bg-gray-200 dark:bg-gray-700 rounded w-1/3" />
      <div className="h-64 bg-gray-200 dark:bg-gray-700 rounded" />
      <div className="h-12 bg-gray-200 dark:bg-gray-700 rounded w-1/2" />
    </div>
  );
}

export default function PlayClient({ id }: { id: string }) {
  const searchParams = useSearchParams();
  const initialMode = (searchParams.get('mode') as 'learn' | 'test') || 'learn';
  const [mode, setMode] = useState<'learn' | 'test'>(initialMode);
  const [gameStarted, setGameStarted] = useState(false);
  const [gameComplete, setGameComplete] = useState(false);
  const [finalScore, setFinalScore] = useState(0);


  const game = useMemo(() => {
    return ACL_GAMES.find(g => g.id === id);
  }, [id]);

  if (!game) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-4">Game Not Found</h1>
          <p className="text-gray-600 dark:text-gray-400 mb-6">
            The game &quot;{id}&quot; could not be found in the demo gallery.
          </p>
          <Link
            href="/acl-demo"
            className="px-4 py-2 bg-primary-500 text-white rounded-lg hover:bg-primary-600"
          >
            Back to Gallery
          </Link>
        </div>
      </div>
    );
  }

  if (!gameStarted) {
    return <ModeSelectionScreen game={game} mode={mode} onModeChange={setMode} onStart={() => setGameStarted(true)} />;
  }

  const handleComplete = (score: number) => {
    setFinalScore(score);
    setGameComplete(true);
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      {/* Top bar */}
      <div className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 px-4 py-3">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Link href="/acl-demo" className="text-sm text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300">
              &larr; Gallery
            </Link>
            <span className="text-gray-300 dark:text-gray-600">|</span>
            <span className="text-sm font-medium text-gray-800 dark:text-gray-200">
              {game.title}
            </span>
          </div>
          <div className="flex items-center gap-3">
            <ModeToggle mode={mode} onToggle={(m) => { setMode(m); setGameComplete(false); }} disabled={gameStarted && !gameComplete} />
            <ThemeToggle />
          </div>
        </div>
      </div>

      {/* Game */}
      <div className="max-w-7xl mx-auto px-4 py-6">
        <GameRenderer game={game} mode={mode} onComplete={handleComplete} />
      </div>

    </div>
  );
}

function ModeSelectionScreen({ game, mode, onModeChange, onStart }: {
  game: ACLGameEntry;
  mode: 'learn' | 'test';
  onModeChange: (m: 'learn' | 'test') => void;
  onStart: () => void;
}) {
  const icon = DOMAIN_ICONS[game.domain];
  const domainLabel = DOMAIN_LABELS[game.domain];
  const levelLabel = LEVEL_LABELS[game.educationLevel];
  const mechanicLabel = MECHANIC_LABELS[game.mechanic] || game.mechanic;

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center p-4">
      <div className="max-w-lg w-full bg-white dark:bg-gray-800 rounded-2xl shadow-xl p-8">
        <Link href="/acl-demo" className="text-sm text-gray-500 dark:text-gray-400 hover:underline mb-6 inline-block">
          &larr; Back to Gallery
        </Link>

        <div className="text-center mb-8">
          <span className="text-5xl mb-4 block">{icon}</span>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-2">
            {game.title}
          </h1>
          <div className="flex flex-wrap justify-center gap-2 mb-4">
            <span className="px-2 py-1 text-xs font-medium bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 rounded-full">
              {domainLabel}
            </span>
            <span className="px-2 py-1 text-xs font-medium bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 rounded-full">
              {levelLabel}
            </span>
            <span className="px-2 py-1 text-xs font-medium bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 rounded-full">
              {mechanicLabel}
            </span>
            <span className="px-2 py-1 text-xs font-medium bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 rounded-full">
              {game.bloomsLevel}
            </span>
          </div>
          <p className="text-sm text-gray-600 dark:text-gray-400 max-w-md mx-auto">
            {game.question}
          </p>
        </div>

        {/* Mode selection */}
        <div className="mb-6">
          <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3 text-center">
            Choose your mode
          </h3>
          <div className="flex justify-center mb-4">
            <ModeToggle mode={mode} onToggle={onModeChange} />
          </div>
          <div className="text-center text-sm text-gray-500 dark:text-gray-400">
            {mode === 'learn' ? (
              <p>Hints available, no time pressure, educational feedback after each action.</p>
            ) : (
              <p>No hints, timed, score-focused. Results shown at the end.</p>
            )}
          </div>
        </div>

        {/* Start button */}
        <button
          onClick={onStart}
          className="w-full py-3 bg-gradient-to-r from-primary-500 to-secondary-500 text-white font-semibold rounded-xl hover:from-primary-600 hover:to-secondary-600 shadow-lg hover:shadow-xl transition-all text-lg"
        >
          Start Game
        </button>

      </div>
    </div>
  );
}

function GameRenderer({ game, mode, onComplete }: {
  game: ACLGameEntry;
  mode: 'learn' | 'test';
  onComplete: (score: number) => void;
}) {
  const blueprint = game.blueprint;

  if (game.gameType === 'interactive_diagram') {
    return (
      <InteractiveDiagramGame
        blueprint={blueprint}
        onComplete={onComplete}
        gameplayMode={mode}
      />
    );
  }

  // Algorithm games — route by mechanic / scene structure
  if (game.gameType === 'algorithm') {
    const isMultiScene = blueprint?.scenes && Array.isArray(blueprint.scenes) && blueprint.scenes.length > 1;

    if (isMultiScene) {
      return (
        <AlgorithmMultiSceneGame
          blueprint={blueprint}
          onComplete={onComplete}
          gameplayMode={mode}
        />
      );
    }

    // Determine subtype from mechanic or blueprint
    const subtype = game.mechanic || blueprint?.templateSubType || blueprint?.gameSubType;

    switch (subtype) {
      case 'state_tracer':
        return <StateTracerGame blueprint={blueprint} onComplete={onComplete} gameplayMode={mode} />;
      case 'bug_hunter':
        return <BugHunterGame blueprint={blueprint} onComplete={onComplete} gameplayMode={mode} />;
      case 'algorithm_builder':
        return <AlgorithmBuilderGame blueprint={blueprint} onComplete={onComplete} gameplayMode={mode} />;
      case 'complexity_analyzer':
        return <ComplexityAnalyzerGame blueprint={blueprint} onComplete={onComplete} gameplayMode={mode} />;
      case 'constraint_puzzle':
        return <ConstraintPuzzleGame blueprint={blueprint} onComplete={onComplete} gameplayMode={mode} />;
      default:
        // Fallback: try state tracer
        return <StateTracerGame blueprint={blueprint} onComplete={onComplete} gameplayMode={mode} />;
    }
  }

  return (
    <div className="text-center py-16 text-gray-500 dark:text-gray-400">
      <p>Unsupported game type: {game.gameType}</p>
    </div>
  );
}
