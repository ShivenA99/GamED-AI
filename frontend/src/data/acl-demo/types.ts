export type Domain = 'biology' | 'history' | 'cs' | 'mathematics' | 'linguistics';
export type EducationLevel = 'k12' | 'undergraduate' | 'graduate';
export type GameType = 'interactive_diagram' | 'algorithm';
export type BloomsLevel = 'Remember' | 'Understand' | 'Apply' | 'Analyze' | 'Evaluate' | 'Create';

export interface PipelineMetrics {
  runId: string;
  totalTokens: number;
  totalCost: number;
  latencySeconds: number;
  validationPassRate: number;
  modelUsed: string;
  agentCount: number;
  timestamp: string;
}

export interface ACLGameEntry {
  id: string;
  title: string;
  question: string;
  domain: Domain;
  educationLevel: EducationLevel;
  gameType: GameType;
  mechanic: string;
  bloomsLevel: BloomsLevel;
  pipelineMetrics: PipelineMetrics;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  blueprint: any;
}

export interface AggregateMetrics {
  totalGames: number;
  totalTokens: number;
  totalCost: number;
  avgTokensPerGame: number;
  avgCostPerGame: number;
  avgLatencySeconds: number;
  avgValidationPassRate: number;
  byDomain: Record<Domain, DomainMetrics>;
  byLevel: Record<EducationLevel, LevelMetrics>;
  byMechanic: Record<string, MechanicMetrics>;
}

export interface DomainMetrics {
  count: number;
  avgCost: number;
  avgTokens: number;
  avgLatency: number;
  avgVPR: number;
}

export interface LevelMetrics {
  count: number;
  avgCost: number;
  avgTokens: number;
  avgLatency: number;
  avgVPR: number;
}

export interface MechanicMetrics {
  count: number;
  avgCost: number;
  avgTokens: number;
  avgLatency: number;
  avgVPR: number;
}

// Display helpers
export const DOMAIN_LABELS: Record<Domain, string> = {
  biology: 'Biology',
  history: 'History',
  cs: 'Computer Science',
  mathematics: 'Mathematics',
  linguistics: 'Linguistics',
};

export const DOMAIN_COLORS: Record<Domain, { bg: string; text: string; border: string }> = {
  biology: { bg: 'bg-green-50 dark:bg-green-900/20', text: 'text-green-700 dark:text-green-300', border: 'border-green-200 dark:border-green-800' },
  history: { bg: 'bg-amber-50 dark:bg-amber-900/20', text: 'text-amber-700 dark:text-amber-300', border: 'border-amber-200 dark:border-amber-800' },
  cs: { bg: 'bg-blue-50 dark:bg-blue-900/20', text: 'text-blue-700 dark:text-blue-300', border: 'border-blue-200 dark:border-blue-800' },
  mathematics: { bg: 'bg-purple-50 dark:bg-purple-900/20', text: 'text-purple-700 dark:text-purple-300', border: 'border-purple-200 dark:border-purple-800' },
  linguistics: { bg: 'bg-rose-50 dark:bg-rose-900/20', text: 'text-rose-700 dark:text-rose-300', border: 'border-rose-200 dark:border-rose-800' },
};

export const DOMAIN_ICONS: Record<Domain, string> = {
  biology: '\u{1F9EC}',
  history: '\u{1F3DB}',
  cs: '\u{1F4BB}',
  mathematics: '\u{1F4D0}',
  linguistics: '\u{1F4AC}',
};

export const LEVEL_LABELS: Record<EducationLevel, string> = {
  k12: 'K-12',
  undergraduate: 'Undergraduate',
  graduate: 'Graduate',
};

export const MECHANIC_LABELS: Record<string, string> = {
  drag_drop: 'Drag & Drop',
  sequencing: 'Sequencing',
  click_to_identify: 'Click to Identify',
  trace_path: 'Trace Path',
  sorting_categories: 'Sorting',
  memory_match: 'Memory Match',
  branching_scenario: 'Branching',
  compare_contrast: 'Compare',
  description_matching: 'Description Match',
  state_tracer: 'State Tracer',
  bug_hunter: 'Bug Hunter',
  algorithm_builder: 'Algorithm Builder',
  complexity_analyzer: 'Complexity Analyzer',
  constraint_puzzle: 'Constraint Puzzle',
  hierarchical: 'Hierarchical',
};
