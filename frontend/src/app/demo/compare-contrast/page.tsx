'use client';

import { useCallback } from 'react';
import { useTheme } from 'next-themes';
import Link from 'next/link';
import dynamic from 'next/dynamic';
import { compareContrastDemo } from '@/components/templates/InteractiveDiagramGame/data';

const InteractiveDiagramGame = dynamic(
  () => import('@/components/templates/InteractiveDiagramGame'),
  { ssr: false }
);

export default function CompareContrastDemoPage() {
  const { resolvedTheme } = useTheme();
  const isDark = (resolvedTheme || 'dark') === 'dark';

  const handleComplete = useCallback((score: number) => {
    console.log('[CompareContrast Demo] Final score:', score);
  }, []);

  return (
    <div className={`min-h-screen py-8 px-4 ${isDark ? 'bg-background' : 'bg-background'}`}>
      <div className="max-w-6xl mx-auto">
        <Link
          href="/"
          className={`inline-block mb-4 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
            isDark
              ? 'bg-gray-800 text-gray-300 hover:bg-gray-700'
              : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
          }`}
        >
          &larr; Back to Home
        </Link>
        <div className="mb-6 text-center">
          <span className="text-3xl mb-2 block">⚖️</span>
          <h1 className={`text-2xl font-bold mb-1 ${isDark ? 'text-foreground' : 'text-foreground'}`}>
            Compare &amp; Contrast Demo
          </h1>
          <p className="text-muted-foreground text-sm">Compare structures between plant and animal cells</p>
        </div>
        <InteractiveDiagramGame
          blueprint={compareContrastDemo}
          onComplete={handleComplete}
        />
      </div>
    </div>
  );
}
