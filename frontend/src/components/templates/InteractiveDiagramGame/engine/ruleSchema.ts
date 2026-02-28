/**
 * ruleSchema.ts — JSON rule format type definitions.
 * Defines the target schema for backend-generated rules (Layer 1).
 * json-rules-engine is NOT installed yet — this is purely types.
 * No runtime code, no React, no Zustand.
 */

/** Rule condition operators (json-rules-engine compatible) */
export type RuleOperator =
  | 'equal' | 'notEqual'
  | 'greaterThan' | 'greaterThanInclusive'
  | 'lessThan' | 'lessThanInclusive'
  | 'in' | 'notIn' | 'contains'
  // Custom operators (registered when json-rules-engine is added)
  | 'isExactSequence' | 'isPlacedCorrectly'
  | 'allZonesLabeled' | 'waypointVisited';

export interface RuleCondition {
  fact: string;
  operator: RuleOperator;
  value: unknown;
}

export interface RuleConditionGroup {
  all?: (RuleCondition | RuleConditionGroup)[];
  any?: (RuleCondition | RuleConditionGroup)[];
}

export type RuleEvent =
  | { type: 'score_update'; params: { delta: number; formula?: string } }
  | { type: 'feedback'; params: { message: string; severity: string } }
  | { type: 'mechanic_complete'; params: { mechanic: string } }
  | { type: 'mode_transition'; params: { to: string; animation?: string } }
  | { type: 'scene_transition'; params: { to_scene: string } }
  | { type: 'game_complete'; params: Record<string, never> };

export interface GameRule {
  id: string;
  priority?: number;
  conditions: RuleConditionGroup;
  event: RuleEvent;
}

/** A full ruleset attached to a blueprint */
export interface GameRuleset {
  version: string;
  rules: GameRule[];
}
