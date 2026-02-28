import {
  BugHunterBlueprint,
  BugDefinition,
  NormalizedBugHunterBlueprint,
  NormalizedBugDefinition,
  BugHunterRound,
} from '../types';

/**
 * Normalize a single BugDefinition to always have multi-line arrays.
 * Old format: lineNumber, buggyLineText, correctLineText (single values)
 * New format: bugLines[], buggyLinesText[], correctLinesText[] (arrays)
 */
export function normalizeBug(bug: BugDefinition): NormalizedBugDefinition {
  return {
    ...bug,
    bugLines: bug.bugLines ?? (bug.lineNumber != null ? [bug.lineNumber] : []),
    buggyLinesText: bug.buggyLinesText ?? (bug.buggyLineText ? [bug.buggyLineText] : []),
    correctLinesText: bug.correctLinesText ?? (bug.correctLineText ? [bug.correctLineText] : []),
    // Keep backward-compat aliases in sync
    lineNumber: bug.lineNumber ?? (bug.bugLines?.[0] ?? 0),
    buggyLineText: bug.buggyLineText ?? (bug.buggyLinesText?.[0] ?? ''),
    correctLineText: bug.correctLineText ?? (bug.correctLinesText?.[0] ?? ''),
  };
}

function normalizeRound(round: BugHunterRound): BugHunterRound {
  return {
    ...round,
    bugs: round.bugs.map(normalizeBug),
  };
}

/**
 * Normalize a BugHunterBlueprint:
 * - If it has rounds[], use them directly.
 * - If it uses the single-code format (buggyCode/bugs/testCases), wrap in 1 round.
 * - All BugDefinitions are normalized to multi-line format.
 */
export function normalizeBugHunterBlueprint(
  bp: BugHunterBlueprint,
): NormalizedBugHunterBlueprint {
  if (bp.rounds && bp.rounds.length > 0) {
    return {
      algorithmName: bp.algorithmName,
      algorithmDescription: bp.algorithmDescription,
      narrativeIntro: bp.narrativeIntro,
      language: bp.language,
      rounds: bp.rounds.map(normalizeRound),
      config: bp.config,
    };
  }

  // Single-code → wrap in 1 round
  return {
    algorithmName: bp.algorithmName,
    algorithmDescription: bp.algorithmDescription,
    narrativeIntro: bp.narrativeIntro,
    language: bp.language,
    rounds: [
      normalizeRound({
        roundId: 'round-1',
        title: bp.algorithmName,
        buggyCode: bp.buggyCode ?? '',
        correctCode: bp.correctCode ?? '',
        bugs: bp.bugs ?? [],
        testCases: bp.testCases ?? [],
        redHerrings: bp.redHerrings ?? [],
      }),
    ],
    config: bp.config,
  };
}
