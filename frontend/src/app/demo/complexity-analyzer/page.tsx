'use client';

import { useState, useCallback } from 'react';
import { useTheme } from 'next-themes';
import { motion } from 'framer-motion';
import ComplexityAnalyzerGame from '@/components/templates/AlgorithmGame/ComplexityAnalyzerGame';
import { ComplexityAnalyzerBlueprint } from '@/components/templates/AlgorithmGame/types';
import { allComplexityAnalyzerDemos } from '@/components/templates/AlgorithmGame/data/complexityAnalyzerIndex';

interface DemoCard {
  id: string;
  name: string;
  challengeCount: number;
  maxPoints: number;
  demo: ComplexityAnalyzerBlueprint;
}

const DEMO_CARDS: DemoCard[] = allComplexityAnalyzerDemos.map((d) => ({
  id: d.id,
  name: d.demo.algorithmName,
  challengeCount: d.demo.challenges.length,
  maxPoints: d.demo.challenges.reduce((s, c) => s + c.points, 0) + 200,
  demo: d.demo,
}));

export default function ComplexityAnalyzerDemoPage() {
  const { resolvedTheme } = useTheme();
  const theme = (resolvedTheme as 'dark' | 'light') || 'dark';
  const isDark = theme === 'dark';

  const [selectedDemo, setSelectedDemo] = useState<DemoCard | null>(null);

  const handleComplete = useCallback((score: number) => {
    console.log('[ComplexityAnalyzer Demo] Final score:', score);
  }, []);

  if (selectedDemo) {
    return (
      <div className={`min-h-screen py-8 px-4 ${isDark ? 'bg-background' : 'bg-background'}`}>
        <div className="max-w-4xl mx-auto">
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
          <ComplexityAnalyzerGame
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
            Complexity Analyzer
          </h1>
          <p className={`${isDark ? 'text-muted-foreground' : 'text-muted-foreground'}`}>
            Analyze code, growth data, and multi-section algorithms to determine Big-O complexity
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
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
              className={`text-left p-5 rounded-xl border-2 transition-all cursor-pointer bg-gradient-to-br from-purple-500/20 to-purple-600/10 ${
                isDark
                  ? 'border-purple-500/30 hover:border-purple-400 hover:bg-gray-800/50'
                  : 'border-purple-500/30 hover:border-purple-400 hover:bg-gray-50'
              }`}
            >
              <div className="text-2xl mb-2">{'\u{1F4CA}'}</div>
              <h3
                className={`font-bold text-lg mb-1 ${
                  isDark ? 'text-foreground' : 'text-foreground'
                }`}
              >
                {card.name}
              </h3>
              <div className="flex items-center gap-2 mt-2">
                <span
                  className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                    isDark
                      ? 'bg-purple-900/40 text-purple-400'
                      : 'bg-purple-100 text-purple-700'
                  }`}
                >
                  {card.challengeCount} challenges
                </span>
                <span className={`text-xs ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>
                  {card.maxPoints} max pts
                </span>
              </div>
            </motion.button>
          ))}
        </div>
      </div>
    </div>
  );
}
