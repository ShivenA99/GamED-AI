'use client';

import { useState, useCallback } from 'react';
import { useTheme } from 'next-themes';
import { motion } from 'framer-motion';
import BugHunterGame from '@/components/templates/AlgorithmGame/BugHunterGame';
import { BugHunterBlueprint } from '@/components/templates/AlgorithmGame/types';
import { allBugHunterDemos } from '@/components/templates/AlgorithmGame/data/bugHunterIndex';

interface DemoCard {
  id: string;
  name: string;
  bugs: number;
  difficulty: string;
  color: string;
  borderColor: string;
  icon: string;
  demo: BugHunterBlueprint;
}

const DEMO_CARDS: DemoCard[] = allBugHunterDemos.map((d) => {
  // Handle both single-code and rounds mode
  const allBugs = d.demo.rounds
    ? d.demo.rounds.flatMap((r) => r.bugs)
    : (d.demo.bugs ?? []);
  const maxDiff = allBugs.length > 0 ? Math.max(...allBugs.map((b) => b.difficulty)) : 1;
  const difficulty = maxDiff === 1 ? 'Easy' : maxDiff === 2 ? 'Medium' : 'Hard';

  const diffColors: Record<string, { color: string; borderColor: string }> = {
    Easy: { color: 'from-green-500/20 to-green-600/10', borderColor: 'border-green-500/30 hover:border-green-400' },
    Medium: { color: 'from-yellow-500/20 to-yellow-600/10', borderColor: 'border-yellow-500/30 hover:border-yellow-400' },
    Hard: { color: 'from-red-500/20 to-red-600/10', borderColor: 'border-red-500/30 hover:border-red-400' },
  };

  const { color, borderColor } = diffColors[difficulty] || diffColors.Medium;

  const isRounds = !!(d.demo.rounds && d.demo.rounds.length > 1);
  const isFreeText = d.demo.config.fixMode === 'free_text';

  return {
    id: d.id,
    name: d.demo.algorithmName,
    bugs: allBugs.length,
    difficulty,
    color,
    borderColor,
    icon: isRounds ? '\u{1F3AF}' : isFreeText ? '\u{270D}\u{FE0F}' : '\u{1F41B}',
    demo: d.demo,
  };
});

export default function BugHunterDemoPage() {
  const { resolvedTheme } = useTheme();
  const theme = (resolvedTheme as 'dark' | 'light') || 'dark';
  const isDark = theme === 'dark';

  const [selectedDemo, setSelectedDemo] = useState<DemoCard | null>(null);

  const handleComplete = useCallback((score: number) => {
    console.log('[BugHunter Demo] Final score:', score);
  }, []);

  if (selectedDemo) {
    return (
      <div className={`min-h-screen py-8 px-4 ${isDark ? 'bg-background' : 'bg-background'}`}>
        <div className="max-w-6xl mx-auto">
          <button
            onClick={() => setSelectedDemo(null)}
            className={`mb-4 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              isDark
                ? 'bg-gray-800 text-gray-300 hover:bg-gray-700'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            &larr; Back to Demos
          </button>
          <BugHunterGame
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
            Bug Hunter — Algorithm Demos
          </h1>
          <p className={`${isDark ? 'text-muted-foreground' : 'text-muted-foreground'}`}>
            Find and fix bugs in algorithm implementations
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {DEMO_CARDS.map((card, i) => (
            <motion.button
              key={card.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.05, type: 'spring', stiffness: 300, damping: 25 }}
              onClick={() => setSelectedDemo(card)}
              className={`text-left p-5 rounded-xl border-2 transition-all cursor-pointer bg-gradient-to-br ${card.color} ${card.borderColor} ${
                isDark ? 'hover:bg-gray-800/50' : 'hover:bg-gray-50'
              }`}
            >
              <div className={`text-2xl mb-2`}>
                {card.icon}
              </div>
              <h3 className={`font-bold text-lg mb-1 ${isDark ? 'text-foreground' : 'text-foreground'}`}>
                {card.name}
              </h3>
              <div className="flex items-center gap-2 mt-2">
                <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                  card.difficulty === 'Easy'
                    ? isDark ? 'bg-green-900/40 text-green-400' : 'bg-green-100 text-green-700'
                    : card.difficulty === 'Medium'
                    ? isDark ? 'bg-yellow-900/40 text-yellow-400' : 'bg-yellow-100 text-yellow-700'
                    : isDark ? 'bg-red-900/40 text-red-400' : 'bg-red-100 text-red-700'
                }`}>
                  {card.difficulty}
                </span>
                <span className={`text-xs ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>
                  {card.bugs} bug{card.bugs > 1 ? 's' : ''}
                </span>
              </div>
            </motion.button>
          ))}
        </div>
      </div>
    </div>
  );
}
