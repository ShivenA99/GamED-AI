'use client';

import { useState, useCallback } from 'react';
import { useTheme } from 'next-themes';
import { motion } from 'framer-motion';
import CombinedPuzzleGame from '@/components/templates/AlgorithmGame/CombinedPuzzleGame';
import { allCombinedPuzzleDemos, CombinedPuzzleDemoEntry } from '@/components/templates/AlgorithmGame/data/combinedPuzzleIndex';

const CARD_STYLES: Record<string, { color: string; borderColor: string }> = {
  knapsack: {
    color: 'from-green-500/20 to-green-600/10',
    borderColor: 'border-green-500/30 hover:border-green-400',
  },
  mst: {
    color: 'from-cyan-500/20 to-cyan-600/10',
    borderColor: 'border-cyan-500/30 hover:border-cyan-400',
  },
  activity: {
    color: 'from-blue-500/20 to-blue-600/10',
    borderColor: 'border-blue-500/30 hover:border-blue-400',
  },
  coloring: {
    color: 'from-pink-500/20 to-pink-600/10',
    borderColor: 'border-pink-500/30 hover:border-pink-400',
  },
};

const CARD_KEYS = ['knapsack', 'mst', 'activity', 'coloring'];

function getCardStyle(index: number) {
  const key = CARD_KEYS[index] ?? 'knapsack';
  return CARD_STYLES[key] ?? CARD_STYLES.knapsack;
}

export default function CombinedPuzzleDemoPage() {
  const { resolvedTheme } = useTheme();
  const theme = (resolvedTheme as 'dark' | 'light') || 'dark';
  const isDark = theme === 'dark';

  const [selectedDemo, setSelectedDemo] = useState<CombinedPuzzleDemoEntry | null>(null);

  const handleComplete = useCallback((score: number) => {
    console.log('[CombinedPuzzle Demo] Final score:', score);
  }, []);

  if (selectedDemo) {
    return (
      <div className={`min-h-screen py-8 px-4 ${isDark ? 'bg-background' : 'bg-background'}`}>
        <div className="max-w-[1400px] mx-auto">
          <button
            onClick={() => setSelectedDemo(null)}
            className={`mb-4 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              isDark
                ? 'bg-gray-800 text-gray-300 hover:bg-gray-700'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            &larr; Back to Challenges
          </button>
          <CombinedPuzzleGame
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
          <h1 className={`text-3xl font-bold mb-2 ${isDark ? 'text-foreground' : 'text-foreground'}`}>
            Combined Puzzle + Code
          </h1>
          <p className={`${isDark ? 'text-muted-foreground' : 'text-muted-foreground'}`}>
            Write the algorithm AND solve the puzzle manually. Bonus points when both solutions match!
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {allCombinedPuzzleDemos.map((entry, i) => {
            const style = getCardStyle(i);
            const demo = entry.demo;
            const modeLabel =
              demo.algorithmChallenge.mode === 'parsons'
                ? 'Parsons Blocks'
                : demo.algorithmChallenge.mode === 'free_code'
                  ? 'Free Code'
                  : 'Parsons + Free Code';

            return (
              <motion.button
                key={entry.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{
                  delay: i * 0.05,
                  type: 'spring',
                  stiffness: 300,
                  damping: 25,
                }}
                onClick={() => setSelectedDemo(entry)}
                className={`text-left p-5 rounded-xl border-2 transition-all cursor-pointer bg-gradient-to-br ${style.color} ${style.borderColor} ${
                  isDark ? 'hover:bg-gray-800/50' : 'hover:bg-gray-50'
                }`}
              >
                <div className="text-3xl mb-2">{demo.icon}</div>
                <h3 className={`font-bold text-lg mb-1 ${isDark ? 'text-foreground' : 'text-foreground'}`}>
                  {demo.title}
                </h3>
                <p className={`text-xs mb-2 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
                  {demo.description}
                </p>
                <div className="flex gap-2">
                  <span className={`text-[10px] px-2 py-0.5 rounded-full ${
                    isDark ? 'bg-blue-900/30 text-blue-400' : 'bg-blue-100 text-blue-700'
                  }`}>
                    {modeLabel}
                  </span>
                  <span className={`text-[10px] px-2 py-0.5 rounded-full ${
                    isDark ? 'bg-purple-900/30 text-purple-400' : 'bg-purple-100 text-purple-700'
                  }`}>
                    {demo.puzzleBlueprint.boardConfig.boardType.replace('_', ' ')}
                  </span>
                </div>
              </motion.button>
            );
          })}
        </div>
      </div>
    </div>
  );
}
