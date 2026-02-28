'use client';

import type { AggregateMetrics } from '@/data/acl-demo/types';
import { DOMAIN_LABELS, LEVEL_LABELS, MECHANIC_LABELS } from '@/data/acl-demo/types';

interface MetricsDashboardProps {
  metrics: AggregateMetrics;
}

export default function MetricsDashboard({ metrics }: MetricsDashboardProps) {
  if (metrics.totalGames === 0) return null;

  return (
    <div className="space-y-8">
      {/* Summary cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <SummaryCard label="Total Games" value={metrics.totalGames.toString()} />
        <SummaryCard label="Avg Cost" value={`$${metrics.avgCostPerGame.toFixed(2)}`} />
        <SummaryCard label="Avg Tokens" value={formatNumber(metrics.avgTokensPerGame)} />
        <SummaryCard label="Avg VPR" value={`${(metrics.avgValidationPassRate * 100).toFixed(0)}%`} />
      </div>

      {/* Distribution charts */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <BarChart
          title="Games by Domain"
          data={Object.entries(metrics.byDomain).map(([key, val]) => ({
            label: DOMAIN_LABELS[key as keyof typeof DOMAIN_LABELS] || key,
            value: val.count,
          }))}
          color="bg-primary-500"
        />
        <BarChart
          title="Games by Level"
          data={Object.entries(metrics.byLevel).map(([key, val]) => ({
            label: LEVEL_LABELS[key as keyof typeof LEVEL_LABELS] || key,
            value: val.count,
          }))}
          color="bg-secondary-500"
        />
        <BarChart
          title="Games by Mechanic"
          data={Object.entries(metrics.byMechanic)
            .sort((a, b) => b[1].count - a[1].count)
            .map(([key, val]) => ({
              label: MECHANIC_LABELS[key] || key,
              value: val.count,
            }))}
          color="bg-violet-500"
        />
      </div>

      {/* Detailed table */}
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-200 dark:border-gray-700">
              <th className="text-left px-3 py-2 text-gray-500 dark:text-gray-400">Category</th>
              <th className="text-right px-3 py-2 text-gray-500 dark:text-gray-400">Games</th>
              <th className="text-right px-3 py-2 text-gray-500 dark:text-gray-400">Avg Cost</th>
              <th className="text-right px-3 py-2 text-gray-500 dark:text-gray-400">Avg Tokens</th>
              <th className="text-right px-3 py-2 text-gray-500 dark:text-gray-400">Avg Latency</th>
              <th className="text-right px-3 py-2 text-gray-500 dark:text-gray-400">Avg VPR</th>
            </tr>
          </thead>
          <tbody>
            <tr className="bg-gray-50 dark:bg-gray-800/50">
              <td colSpan={6} className="px-3 py-1.5 text-xs font-bold text-gray-500 dark:text-gray-400 uppercase tracking-wider">By Domain</td>
            </tr>
            {Object.entries(metrics.byDomain).map(([key, val]) => (
              <MetricsRow
                key={key}
                label={DOMAIN_LABELS[key as keyof typeof DOMAIN_LABELS] || key}
                count={val.count}
                avgCost={val.avgCost}
                avgTokens={val.avgTokens}
                avgLatency={val.avgLatency}
                avgVPR={val.avgVPR}
              />
            ))}
            <tr className="bg-gray-50 dark:bg-gray-800/50">
              <td colSpan={6} className="px-3 py-1.5 text-xs font-bold text-gray-500 dark:text-gray-400 uppercase tracking-wider">By Level</td>
            </tr>
            {Object.entries(metrics.byLevel).map(([key, val]) => (
              <MetricsRow
                key={key}
                label={LEVEL_LABELS[key as keyof typeof LEVEL_LABELS] || key}
                count={val.count}
                avgCost={val.avgCost}
                avgTokens={val.avgTokens}
                avgLatency={val.avgLatency}
                avgVPR={val.avgVPR}
              />
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function SummaryCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
      <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">{label}</div>
      <div className="text-2xl font-bold text-gray-900 dark:text-gray-100">{value}</div>
    </div>
  );
}

function BarChart({ title, data, color }: { title: string; data: { label: string; value: number }[]; color: string }) {
  const maxVal = Math.max(...data.map(d => d.value), 1);

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
      <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">{title}</h3>
      <div className="space-y-2">
        {data.map(item => (
          <div key={item.label} className="flex items-center gap-2">
            <span className="text-xs text-gray-600 dark:text-gray-400 w-24 truncate" title={item.label}>
              {item.label}
            </span>
            <div className="flex-1 h-4 bg-gray-100 dark:bg-gray-700 rounded-full overflow-hidden">
              <div
                className={`h-full ${color} rounded-full transition-all duration-500`}
                style={{ width: `${(item.value / maxVal) * 100}%` }}
              />
            </div>
            <span className="text-xs font-semibold text-gray-700 dark:text-gray-300 w-6 text-right">
              {item.value}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

function MetricsRow({ label, count, avgCost, avgTokens, avgLatency, avgVPR }: {
  label: string; count: number; avgCost: number; avgTokens: number; avgLatency: number; avgVPR: number;
}) {
  return (
    <tr className="border-b border-gray-100 dark:border-gray-700/50">
      <td className="px-3 py-2 text-gray-700 dark:text-gray-300">{label}</td>
      <td className="text-right px-3 py-2 font-medium text-gray-800 dark:text-gray-200">{count}</td>
      <td className="text-right px-3 py-2 text-gray-600 dark:text-gray-400">${avgCost.toFixed(2)}</td>
      <td className="text-right px-3 py-2 text-gray-600 dark:text-gray-400">{formatNumber(avgTokens)}</td>
      <td className="text-right px-3 py-2 text-gray-600 dark:text-gray-400">{avgLatency.toFixed(0)}s</td>
      <td className="text-right px-3 py-2 text-gray-600 dark:text-gray-400">{(avgVPR * 100).toFixed(0)}%</td>
    </tr>
  );
}

function formatNumber(n: number): string {
  if (n >= 1000000) return `${(n / 1000000).toFixed(1)}M`;
  if (n >= 1000) return `${(n / 1000).toFixed(1)}k`;
  return Math.round(n).toString();
}
