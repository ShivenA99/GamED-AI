import type { ACLGameEntry, AggregateMetrics } from './types';

// Import game JSON files.
// After pipeline generation, each game is saved as a JSON file in ./games/.
// We use explicit try/catch requires so that missing files don't break the build.
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const _imports: Record<string, any> = {};

// Attempt to load each game file — files that don't exist yet are silently skipped.
// After running generate_acl_demo.py, the JSON files will be available.
const GAME_IDS = [
  // Biology (10 interactive diagram)
  'bio-k12-plant-cell-drag-drop',
  'bio-k12-mitosis-sequencing',
  'bio-k12-food-chains-sorting',
  'bio-undergrad-organelles-click-identify',
  'bio-undergrad-cardiovascular-trace-path',
  'bio-undergrad-dna-enzymes-description',
  'bio-undergrad-inheritance-memory',
  'bio-grad-clinical-diagnosis-branching',
  'bio-grad-evolution-mechanisms-compare',
  'bio-grad-cellular-respiration-trace-path',
  // History (10 interactive diagram)
  'hist-k12-american-revolution-sequencing',
  'hist-k12-historical-figures-memory',
  'hist-k12-roman-empire-trace-path',
  'hist-undergrad-wwi-causes-sorting',
  'hist-undergrad-revolutions-compare',
  'hist-undergrad-industrial-revolution-drag-drop',
  'hist-undergrad-ancient-civilizations-click-identify',
  'hist-grad-historiographic-description',
  'hist-grad-versailles-branching',
  'hist-grad-cold-war-sequencing',
  // CS (5 interactive diagram + 5 algorithm)
  'cs-k12-computer-parts-drag-drop',
  'cs-k12-network-data-trace-path',
  'cs-k12-bubble-sort-state-tracer',
  'cs-undergrad-uml-click-identify',
  'cs-undergrad-algorithm-complexity-sorting',
  'cs-undergrad-binary-search-bug-hunter',
  'cs-undergrad-bfs-algorithm-builder',
  'cs-grad-tcp-udp-compare',
  'cs-grad-dp-complexity-analyzer',
  'cs-grad-scheduling-constraint-puzzle',
  // Mathematics (10 interactive diagram)
  'math-k12-geometry-drag-drop',
  'math-k12-linear-equation-sequencing',
  'math-k12-number-types-sorting',
  'math-undergrad-calculus-description-matching',
  'math-undergrad-matrix-ops-memory',
  'math-undergrad-function-types-click-identify',
  'math-undergrad-integration-trace-path',
  'math-grad-proof-strategy-branching',
  'math-grad-numerical-methods-compare',
  'math-grad-vector-spaces-drag-drop',
  // Linguistics (10 interactive diagram)
  'ling-k12-sentence-parts-drag-drop',
  'ling-k12-word-types-sorting',
  'ling-k12-sentence-building-sequencing',
  'ling-undergrad-phonology-trace-path',
  'ling-undergrad-morphemes-click-identify',
  'ling-undergrad-language-families-memory',
  'ling-undergrad-semantic-roles-description',
  'ling-grad-syntax-trees-compare',
  'ling-grad-language-acquisition-branching',
  'ling-grad-phonological-processes-sorting',
] as const;

function tryRequire(id: string): ACLGameEntry | null {
  try {
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    return require(`./games/${id}.json`) as ACLGameEntry;
  } catch {
    return null;
  }
}

function loadGames(): ACLGameEntry[] {
  const games: ACLGameEntry[] = [];
  for (const id of GAME_IDS) {
    const game = _imports[id] ?? tryRequire(id);
    if (game) {
      games.push(game);
    }
  }
  return games;
}

export const ACL_GAMES: ACLGameEntry[] = loadGames();

// Sort by domain then education level for consistent display
const DOMAIN_ORDER = ['biology', 'history', 'cs', 'mathematics', 'linguistics'];
const LEVEL_ORDER = ['k12', 'undergraduate', 'graduate'];

ACL_GAMES.sort((a, b) => {
  const domainDiff = DOMAIN_ORDER.indexOf(a.domain) - DOMAIN_ORDER.indexOf(b.domain);
  if (domainDiff !== 0) return domainDiff;
  return LEVEL_ORDER.indexOf(a.educationLevel) - LEVEL_ORDER.indexOf(b.educationLevel);
});

// Compute aggregate metrics from loaded games
export function computeAggregateMetrics(games: ACLGameEntry[]): AggregateMetrics {
  const totalGames = games.length;
  if (totalGames === 0) {
    return {
      totalGames: 0,
      totalTokens: 0,
      totalCost: 0,
      avgTokensPerGame: 0,
      avgCostPerGame: 0,
      avgLatencySeconds: 0,
      avgValidationPassRate: 0,
      byDomain: {} as AggregateMetrics['byDomain'],
      byLevel: {} as AggregateMetrics['byLevel'],
      byMechanic: {},
    };
  }

  const totalTokens = games.reduce((sum, g) => sum + g.pipelineMetrics.totalTokens, 0);
  const totalCost = games.reduce((sum, g) => sum + g.pipelineMetrics.totalCost, 0);
  const avgLatency = games.reduce((sum, g) => sum + g.pipelineMetrics.latencySeconds, 0) / totalGames;
  const avgVPR = games.reduce((sum, g) => sum + g.pipelineMetrics.validationPassRate, 0) / totalGames;

  const groupBy = <K extends string>(
    items: ACLGameEntry[],
    keyFn: (g: ACLGameEntry) => K
  ): Record<K, { count: number; avgCost: number; avgTokens: number; avgLatency: number; avgVPR: number }> => {
    const groups: Record<string, ACLGameEntry[]> = {};
    for (const item of items) {
      const key = keyFn(item);
      if (!groups[key]) groups[key] = [];
      groups[key].push(item);
    }
    const result: Record<string, { count: number; avgCost: number; avgTokens: number; avgLatency: number; avgVPR: number }> = {};
    for (const [key, group] of Object.entries(groups)) {
      const n = group.length;
      result[key] = {
        count: n,
        avgCost: group.reduce((s, g) => s + g.pipelineMetrics.totalCost, 0) / n,
        avgTokens: group.reduce((s, g) => s + g.pipelineMetrics.totalTokens, 0) / n,
        avgLatency: group.reduce((s, g) => s + g.pipelineMetrics.latencySeconds, 0) / n,
        avgVPR: group.reduce((s, g) => s + g.pipelineMetrics.validationPassRate, 0) / n,
      };
    }
    return result as Record<K, { count: number; avgCost: number; avgTokens: number; avgLatency: number; avgVPR: number }>;
  };

  return {
    totalGames,
    totalTokens,
    totalCost,
    avgTokensPerGame: totalTokens / totalGames,
    avgCostPerGame: totalCost / totalGames,
    avgLatencySeconds: avgLatency,
    avgValidationPassRate: avgVPR,
    byDomain: groupBy(games, (g) => g.domain),
    byLevel: groupBy(games, (g) => g.educationLevel),
    byMechanic: groupBy(games, (g) => g.mechanic),
  };
}

// Re-export types for convenience
export type { ACLGameEntry, AggregateMetrics } from './types';
export {
  DOMAIN_LABELS,
  DOMAIN_COLORS,
  DOMAIN_ICONS,
  LEVEL_LABELS,
  MECHANIC_LABELS,
} from './types';
