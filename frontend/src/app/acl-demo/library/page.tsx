'use client';

import { useMemo, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { ACL_GAMES, computeAggregateMetrics } from '@/data/acl-demo';
import ACLGameCard from '@/components/acl-demo/ACLGameCard';
import FilterBar, { Filters } from '@/components/acl-demo/FilterBar';
import MetricsDashboard from '@/components/acl-demo/MetricsDashboard';
import type { Domain, EducationLevel } from '@/data/acl-demo/types';

export default function ACLDemoLibraryPage() {
  const searchParams = useSearchParams();

  // Initialize filters from URL search params
  const initialFilters: Filters = {
    domain: (searchParams.get('domain') as Domain | null) || 'all',
    level: (searchParams.get('level') as EducationLevel | null) || 'all',
    type: (searchParams.get('type') as 'interactive_diagram' | 'algorithm' | null) || 'all',
    mechanic: searchParams.get('mechanic') || 'all',
    blooms: searchParams.get('blooms') || 'all',
  };

  const [filters, setFilters] = useState<Filters>(initialFilters);
  const [showMetrics, setShowMetrics] = useState(false);

  const filteredGames = useMemo(() => {
    return ACL_GAMES.filter(game => {
      if (filters.domain !== 'all' && game.domain !== filters.domain) return false;
      if (filters.level !== 'all' && game.educationLevel !== filters.level) return false;
      if (filters.type !== 'all' && game.gameType !== filters.type) return false;
      if (filters.mechanic !== 'all' && game.mechanic !== filters.mechanic) return false;
      if (filters.blooms !== 'all' && game.bloomsLevel !== filters.blooms) return false;
      return true;
    });
  }, [filters]);

  const aggregateMetrics = useMemo(() => computeAggregateMetrics(ACL_GAMES), []);

  const availableMechanics = useMemo(() => {
    const set = new Set(ACL_GAMES.map(g => g.mechanic));
    return Array.from(set).sort();
  }, []);

  const availableBlooms = useMemo(() => {
    const order = ['Remember', 'Understand', 'Apply', 'Analyze', 'Evaluate', 'Create'] as const;
    const set = new Set<string>(ACL_GAMES.map(g => g.bloomsLevel));
    return order.filter(b => set.has(b));
  }, []);

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      {/* Nav */}
      <nav className="border-b border-gray-200/60 dark:border-gray-800 bg-white/80 dark:bg-gray-900/80 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-14 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link href="/acl-demo" className="flex items-center gap-2">
              <span className="text-xl font-bold bg-gradient-to-r from-blue-600 to-violet-600 bg-clip-text text-transparent">
                GamED.AI
              </span>
            </Link>
            <span className="text-gray-300 dark:text-gray-600">|</span>
            <span className="text-sm font-medium text-gray-700 dark:text-gray-300">Game Library</span>
          </div>
          <div className="flex items-center gap-4">
            <button
              onClick={() => setShowMetrics(!showMetrics)}
              className="text-sm font-medium text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100 transition-colors"
            >
              {showMetrics ? 'Hide' : 'Show'} Metrics
            </button>
          </div>
        </div>
      </nav>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {/* Header */}
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-1">
            Game Library
          </h1>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            {ACL_GAMES.length} AI-generated educational games. Each game offers Learn and Test modes.
          </p>
        </div>

        {/* Filters */}
        <div className="mb-6">
          <FilterBar
            filters={filters}
            onChange={setFilters}
            availableMechanics={availableMechanics}
            availableBlooms={availableBlooms}
          />
        </div>

        {/* Results count */}
        <div className="flex items-center justify-between mb-4">
          <p className="text-sm text-gray-600 dark:text-gray-400">
            {filteredGames.length === ACL_GAMES.length
              ? `${ACL_GAMES.length} games`
              : `${filteredGames.length} of ${ACL_GAMES.length} games`}
          </p>
        </div>

        {/* Game grid */}
        {ACL_GAMES.length === 0 ? (
          <div className="text-center py-16">
            <div className="text-5xl mb-4">{'🎮'}</div>
            <h2 className="text-xl font-bold text-gray-900 dark:text-gray-100 mb-2">
              Games Coming Soon
            </h2>
            <p className="text-gray-500 dark:text-gray-400 max-w-md mx-auto">
              The pipeline is generating 50 games across 5 domains. Check back shortly.
            </p>
          </div>
        ) : filteredGames.length === 0 ? (
          <div className="text-center py-16 text-gray-500 dark:text-gray-400">
            <p className="text-lg font-medium mb-2">No games match your filters</p>
            <p className="text-sm">Try adjusting the filters above</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {filteredGames.map(game => (
              <ACLGameCard key={game.id} game={game} />
            ))}
          </div>
        )}

        {/* Metrics dashboard */}
        {showMetrics && aggregateMetrics.totalGames > 0 && (
          <div className="mt-12 pt-8 border-t border-gray-200 dark:border-gray-700">
            <h2 className="text-xl font-bold text-gray-900 dark:text-gray-100 mb-6">
              Pipeline Metrics Dashboard
            </h2>
            <MetricsDashboard metrics={aggregateMetrics} />
          </div>
        )}
      </div>

      {/* Footer */}
      <footer className="mt-16 border-t border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 text-center text-sm text-gray-500 dark:text-gray-400">
          <p>GamED.AI: An Agentic Gamification Platform for Education — ACL 2026</p>
        </div>
      </footer>
    </div>
  );
}
