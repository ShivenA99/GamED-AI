'use client';

import { useState, useCallback } from 'react';
import { useTheme } from 'next-themes';
import { motion } from 'framer-motion';
import StateTracerGame from '@/components/templates/AlgorithmGame/StateTracerGame';
import { StateTracerBlueprint } from '@/components/templates/AlgorithmGame/types';
import { allDemos } from '@/components/templates/AlgorithmGame/data';

interface DemoCard {
  id: string;
  name: string;
  dataStructure: string;
  steps: number;
  color: string;
  borderColor: string;
  icon: string;
  demo: StateTracerBlueprint;
}

const DEMO_CARDS: DemoCard[] = allDemos.map((d) => {
  const colorMap: Record<string, { color: string; borderColor: string; icon: string }> = {
    array: { color: 'from-blue-500/20 to-blue-600/10', borderColor: 'border-blue-500/30 hover:border-blue-400', icon: '[ ]' },
    graph: { color: 'from-purple-500/20 to-purple-600/10', borderColor: 'border-purple-500/30 hover:border-purple-400', icon: '\u25CB\u2192\u25CB' },
    tree: { color: 'from-emerald-500/20 to-emerald-600/10', borderColor: 'border-emerald-500/30 hover:border-emerald-400', icon: '\u25B3' },
    dp_table: { color: 'from-amber-500/20 to-amber-600/10', borderColor: 'border-amber-500/30 hover:border-amber-400', icon: '\u25A6' },
    stack: { color: 'from-red-500/20 to-red-600/10', borderColor: 'border-red-500/30 hover:border-red-400', icon: '\u2593' },
    linked_list: { color: 'from-cyan-500/20 to-cyan-600/10', borderColor: 'border-cyan-500/30 hover:border-cyan-400', icon: '\u2192' },
  };

  const dsType = d.demo.steps[0]?.dataStructure.type || 'array';
  const { color, borderColor, icon } = colorMap[dsType] || colorMap.array;

  return {
    id: d.id,
    name: d.demo.algorithmName,
    dataStructure: dsType.replace('_', ' '),
    steps: d.demo.steps.filter((s) => s.prediction !== null).length,
    color,
    borderColor,
    icon,
    demo: d.demo,
  };
});

export default function StateTracerDemoPage() {
  const { resolvedTheme } = useTheme();
  const theme = (resolvedTheme as 'dark' | 'light') || 'dark';
  const isDark = theme === 'dark';

  const [selectedDemo, setSelectedDemo] = useState<DemoCard | null>(null);

  const handleComplete = useCallback((score: number) => {
    console.log('[StateTracer Demo] Final score:', score);
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
          <StateTracerGame
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
            State Tracer — Algorithm Demos
          </h1>
          <p className={`${isDark ? 'text-muted-foreground' : 'text-muted-foreground'}`}>
            Pick an algorithm to trace step-by-step
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
              <div className={`text-2xl font-mono mb-2 ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
                {card.icon}
              </div>
              <h3 className={`font-bold text-lg mb-1 ${isDark ? 'text-foreground' : 'text-foreground'}`}>
                {card.name}
              </h3>
              <div className="flex items-center gap-2 mt-2">
                <span className={`text-xs px-2 py-0.5 rounded-full font-medium capitalize ${
                  isDark ? 'bg-gray-700 text-gray-300' : 'bg-gray-200 text-gray-600'
                }`}>
                  {card.dataStructure}
                </span>
                <span className={`text-xs ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>
                  {card.steps} predictions
                </span>
              </div>
            </motion.button>
          ))}
        </div>
      </div>
    </div>
  );
}
