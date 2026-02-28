'use client';

import Link from 'next/link';
import type { ACLGameEntry } from '@/data/acl-demo/types';
import {
  DOMAIN_COLORS,
  DOMAIN_ICONS,
  DOMAIN_LABELS,
  LEVEL_LABELS,
  MECHANIC_LABELS,
} from '@/data/acl-demo/types';

interface ACLGameCardProps {
  game: ACLGameEntry;
}

export default function ACLGameCard({ game }: ACLGameCardProps) {
  const colors = DOMAIN_COLORS[game.domain];
  const icon = DOMAIN_ICONS[game.domain];
  const domainLabel = DOMAIN_LABELS[game.domain];
  const levelLabel = LEVEL_LABELS[game.educationLevel];
  const mechanicLabel = MECHANIC_LABELS[game.mechanic] || game.mechanic;

  const metrics = game.pipelineMetrics;

  return (
    <div className={`group relative flex flex-col rounded-xl border ${colors.border} ${colors.bg} overflow-hidden transition-all hover:shadow-lg hover:scale-[1.02]`}>
      {/* Header */}
      <div className="p-4 pb-2">
        <div className="flex items-start justify-between mb-2">
          <span className="text-2xl">{icon}</span>
          <span className={`text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-full ${
            game.gameType === 'algorithm'
              ? 'bg-violet-100 dark:bg-violet-900/30 text-violet-700 dark:text-violet-300'
              : 'bg-cyan-100 dark:bg-cyan-900/30 text-cyan-700 dark:text-cyan-300'
          }`}>
            {game.gameType === 'algorithm' ? 'Algorithm' : 'Diagram'}
          </span>
        </div>
        <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100 line-clamp-2 mb-1.5 min-h-[2.5rem]">
          {game.title}
        </h3>

        {/* Tags */}
        <div className="flex flex-wrap gap-1 mb-2">
          <Tag label={domainLabel} className={colors.text} />
          <Tag label={levelLabel} className="text-gray-600 dark:text-gray-400" />
          <Tag label={mechanicLabel} className="text-gray-600 dark:text-gray-400" />
        </div>

        {/* Bloom's level */}
        <div className="flex items-center gap-1.5 mb-3">
          <span className="text-[10px] text-gray-500 dark:text-gray-400">Bloom&apos;s:</span>
          <BloomsIndicator level={game.bloomsLevel} />
        </div>
      </div>

      {/* Metrics */}
      {metrics && (
        <div className="px-4 py-2 border-t border-gray-200/50 dark:border-gray-700/50 bg-white/50 dark:bg-gray-900/30">
          <div className="grid grid-cols-3 gap-2 text-[10px]">
            <MetricCell label="Cost" value={`$${metrics.totalCost.toFixed(2)}`} />
            <MetricCell label="Tokens" value={formatNumber(metrics.totalTokens)} />
            <MetricCell label="Time" value={`${metrics.latencySeconds.toFixed(0)}s`} />
          </div>
        </div>
      )}

      {/* CTA buttons */}
      <div className="mt-auto px-4 py-3 flex gap-2">
        <Link
          href={`/acl-demo/play/${game.id}?mode=learn`}
          className="flex-1 text-center px-3 py-2 text-xs font-medium bg-blue-500 hover:bg-blue-600 text-white rounded-lg transition-colors"
        >
          Learn
        </Link>
        <Link
          href={`/acl-demo/play/${game.id}?mode=test`}
          className="flex-1 text-center px-3 py-2 text-xs font-medium bg-orange-500 hover:bg-orange-600 text-white rounded-lg transition-colors"
        >
          Test
        </Link>
      </div>
    </div>
  );
}

function Tag({ label, className = '' }: { label: string; className?: string }) {
  return (
    <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded bg-white/60 dark:bg-gray-800/60 ${className}`}>
      {label}
    </span>
  );
}

function MetricCell({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-col items-center">
      <span className="text-gray-400 dark:text-gray-500">{label}</span>
      <span className="font-semibold text-gray-700 dark:text-gray-300">{value}</span>
    </div>
  );
}

function BloomsIndicator({ level }: { level: string }) {
  const levels = ['Remember', 'Understand', 'Apply', 'Analyze', 'Evaluate', 'Create'];
  const idx = levels.indexOf(level);
  const colors = ['bg-gray-400', 'bg-blue-400', 'bg-green-400', 'bg-yellow-400', 'bg-orange-400', 'bg-red-400'];

  return (
    <div className="flex items-center gap-0.5">
      {levels.map((l, i) => (
        <div
          key={l}
          className={`w-2 h-2 rounded-full ${i <= idx ? colors[i] : 'bg-gray-200 dark:bg-gray-700'}`}
          title={l}
        />
      ))}
      <span className="ml-1 text-[10px] font-medium text-gray-600 dark:text-gray-400">{level}</span>
    </div>
  );
}

function formatNumber(n: number): string {
  if (n >= 1000000) return `${(n / 1000000).toFixed(1)}M`;
  if (n >= 1000) return `${(n / 1000).toFixed(1)}k`;
  return n.toString();
}
