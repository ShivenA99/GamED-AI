'use client';

import { useState, useCallback } from 'react';
import { useTheme } from 'next-themes';
import { motion } from 'framer-motion';
import ConstraintPuzzleGame from '@/components/templates/AlgorithmGame/ConstraintPuzzleGame';
import { ConstraintPuzzleBlueprint } from '@/components/templates/AlgorithmGame/types';
import { GenericConstraintPuzzleBlueprint } from '@/components/templates/AlgorithmGame/constraintPuzzle/constraintPuzzleTypes';
import { allConstraintPuzzleDemos } from '@/components/templates/AlgorithmGame/data/constraintPuzzleIndex';

type AnyBlueprint = ConstraintPuzzleBlueprint | GenericConstraintPuzzleBlueprint;

interface DemoCard {
  id: string;
  title: string;
  puzzleType: string;
  icon: string;
  color: string;
  borderColor: string;
  algorithmName: string;
  demo: AnyBlueprint;
}

const PUZZLE_STYLES: Record<string, { icon: string; color: string; borderColor: string }> = {
  knapsack: {
    icon: '\u{1F392}',
    color: 'from-green-500/20 to-green-600/10',
    borderColor: 'border-green-500/30 hover:border-green-400',
  },
  n_queens: {
    icon: '\u265B',
    color: 'from-purple-500/20 to-purple-600/10',
    borderColor: 'border-purple-500/30 hover:border-purple-400',
  },
  coin_change: {
    icon: '\u{1FA99}',
    color: 'from-yellow-500/20 to-yellow-600/10',
    borderColor: 'border-yellow-500/30 hover:border-yellow-400',
  },
  activity_selection: {
    icon: '\u{1F4C5}',
    color: 'from-blue-500/20 to-blue-600/10',
    borderColor: 'border-blue-500/30 hover:border-blue-400',
  },
  // Generic board types
  value_assignment: {
    icon: '\u{1F3A8}',
    color: 'from-pink-500/20 to-pink-600/10',
    borderColor: 'border-pink-500/30 hover:border-pink-400',
  },
  graph_interaction: {
    icon: '\u{1F310}',
    color: 'from-cyan-500/20 to-cyan-600/10',
    borderColor: 'border-cyan-500/30 hover:border-cyan-400',
  },
  sequence_building: {
    icon: '\u{1F4DA}',
    color: 'from-orange-500/20 to-orange-600/10',
    borderColor: 'border-orange-500/30 hover:border-orange-400',
  },
};

const DEFAULT_STYLE = {
  icon: '\u{1F9E9}',
  color: 'from-gray-500/20 to-gray-600/10',
  borderColor: 'border-gray-500/30 hover:border-gray-400',
};

function getPuzzleType(bp: AnyBlueprint): string {
  if ('puzzleType' in bp) return bp.puzzleType;
  return bp.boardConfig.boardType;
}

const DEMO_CARDS: DemoCard[] = allConstraintPuzzleDemos.map((d) => {
  const puzzleType = getPuzzleType(d.demo);
  const style = PUZZLE_STYLES[puzzleType] ?? DEFAULT_STYLE;
  return {
    id: d.id,
    title: d.demo.title,
    puzzleType,
    icon: ('icon' in d.demo && d.demo.icon) ? d.demo.icon : style.icon,
    color: style.color,
    borderColor: style.borderColor,
    algorithmName: d.demo.algorithmName,
    demo: d.demo,
  };
});

export default function ConstraintPuzzleDemoPage() {
  const { resolvedTheme } = useTheme();
  const theme = (resolvedTheme as 'dark' | 'light') || 'dark';
  const isDark = theme === 'dark';

  const [selectedDemo, setSelectedDemo] = useState<DemoCard | null>(null);

  const handleComplete = useCallback((score: number) => {
    console.log('[ConstraintPuzzle Demo] Final score:', score);
  }, []);

  if (selectedDemo) {
    return (
      <div className={`min-h-screen py-8 px-4 ${isDark ? 'bg-background' : 'bg-background'}`}>
        <div className="max-w-3xl mx-auto">
          <button
            onClick={() => setSelectedDemo(null)}
            className={`mb-4 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              isDark
                ? 'bg-gray-800 text-gray-300 hover:bg-gray-700'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            &larr; Back to Puzzles
          </button>
          <ConstraintPuzzleGame
            blueprint={selectedDemo.demo}
            onComplete={handleComplete}
            theme={theme}
          />
        </div>
      </div>
    );
  }

  return (
    <div className={`min-h-screen py-8 px-4 ${isDark ? 'bg-background' : 'bg-background'}`}>
      <div className="max-w-4xl mx-auto">
        <div className="mb-8 text-center">
          <h1
            className={`text-3xl font-bold mb-2 ${
              isDark ? 'text-foreground' : 'text-foreground'
            }`}
          >
            Constraint Puzzle
          </h1>
          <p className={`${isDark ? 'text-muted-foreground' : 'text-muted-foreground'}`}>
            Solve optimization puzzles, then learn the algorithms behind the optimal solutions
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {DEMO_CARDS.map((card, i) => (
            <motion.button
              key={card.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{
                delay: i * 0.05,
                type: 'spring',
                stiffness: 300,
                damping: 25,
              }}
              onClick={() => setSelectedDemo(card)}
              className={`text-left p-5 rounded-xl border-2 transition-all cursor-pointer bg-gradient-to-br ${card.color} ${card.borderColor} ${
                isDark ? 'hover:bg-gray-800/50' : 'hover:bg-gray-50'
              }`}
            >
              <div className="text-3xl mb-2">{card.icon}</div>
              <h3
                className={`font-bold text-lg mb-1 ${
                  isDark ? 'text-foreground' : 'text-foreground'
                }`}
              >
                {card.title}
              </h3>
              <div className={`text-sm mt-1 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
                {card.algorithmName}
              </div>
            </motion.button>
          ))}
        </div>
      </div>
    </div>
  );
}
