import { useMemo } from 'react';
import {
  AlgorithmBuilderBlueprint,
  AlgorithmBuilderScoringState,
  ParsonsBlock,
  BlockFeedback,
} from '../types';

export interface AlgorithmBuilderGradeResult {
  feedback: BlockFeedback[];
  score: number;
  bonuses: { type: string; points: number }[];
  allCorrect: boolean;
}

export function gradeSubmission(
  solutionBlocks: ParsonsBlock[],
  sourceBlocks: ParsonsBlock[],
  blueprint: AlgorithmBuilderBlueprint,
  attempts: number,
  hintPenalty: number,
): AlgorithmBuilderGradeResult {
  const { correct_order, config } = blueprint;
  const feedback: BlockFeedback[] = [];
  let perBlockTotal = 0;

  // Grade blocks placed in the solution
  for (let i = 0; i < solutionBlocks.length; i++) {
    const block = solutionBlocks[i];

    // Distractor incorrectly included
    if (block.is_distractor) {
      feedback.push({
        blockId: block.id,
        status: 'distractor_included',
        pointsAwarded: -30,
      });
      perBlockTotal -= 30;
      continue;
    }

    // Check if this block is at the correct position
    const expectedBlock = correct_order[i];
    const positionCorrect =
      expectedBlock &&
      (expectedBlock.id === block.id ||
        (expectedBlock.group_id != null &&
          expectedBlock.group_id === block.group_id));

    if (positionCorrect) {
      const indentCorrect =
        !config.indentation_matters ||
        block.indent_level === expectedBlock.indent_level;

      if (indentCorrect) {
        feedback.push({ blockId: block.id, status: 'correct', pointsAwarded: 30 });
        perBlockTotal += 30;
      } else {
        feedback.push({
          blockId: block.id,
          status: 'wrong_indent',
          correctIndent: expectedBlock.indent_level,
          pointsAwarded: 15,
        });
        perBlockTotal += 15;
      }
    } else {
      // Find where this block actually belongs
      const correctIdx = correct_order.findIndex(
        (b) =>
          b.id === block.id ||
          (block.group_id != null && b.group_id === block.group_id),
      );
      feedback.push({
        blockId: block.id,
        status: 'wrong_position',
        correctPosition: correctIdx >= 0 ? correctIdx : undefined,
        pointsAwarded: 0,
      });
    }
  }

  // Grade blocks remaining in the source
  for (const block of sourceBlocks) {
    if (block.is_distractor) {
      feedback.push({
        blockId: block.id,
        status: 'distractor_excluded',
        pointsAwarded: 20,
      });
      perBlockTotal += 20;
    } else {
      feedback.push({ blockId: block.id, status: 'missing', pointsAwarded: 0 });
    }
  }

  // Check if all correct
  const allCorrect = feedback.every(
    (f) => f.status === 'correct' || f.status === 'distractor_excluded',
  );

  // Calculate attempt-based score: 300 * 0.8^attempts
  const attemptScore = Math.round(300 * Math.pow(0.8, attempts));

  let score: number;
  const bonuses: { type: string; points: number }[] = [];

  if (allCorrect) {
    score = Math.max(perBlockTotal, attemptScore) - hintPenalty;
    if (attempts === 0) {
      bonuses.push({ type: 'Perfect first try', points: 50 });
      score += 50;
    }
  } else {
    score = Math.max(0, perBlockTotal - hintPenalty);
  }

  return { feedback, score: Math.max(0, score), bonuses, allCorrect };
}

export interface AlgorithmBuilderScoreSummary {
  finalScore: number;
  accuracy: number; // 0-100
  message: string;
}

export function useAlgorithmBuilderScoring(
  scoring: AlgorithmBuilderScoringState,
  totalBlocks: number,
): AlgorithmBuilderScoreSummary {
  return useMemo(() => {
    const finalScore = Math.max(0, scoring.totalScore);

    const correctCount = scoring.perBlockFeedback.filter(
      (f) => f.status === 'correct' || f.status === 'distractor_excluded',
    ).length;
    const accuracy =
      totalBlocks > 0 ? Math.round((correctCount / totalBlocks) * 100) : 0;

    const message =
      accuracy === 100 && scoring.attempts <= 1
        ? 'Perfect! You built the algorithm flawlessly on your first try!'
        : accuracy === 100
          ? 'Great work! You correctly assembled the entire algorithm.'
          : accuracy >= 70
            ? 'Good progress! Most blocks are in the right place.'
            : accuracy >= 40
              ? 'Keep going! Review the feedback and try rearranging.'
              : 'Take your time — read the problem description and hints carefully.';

    return { finalScore, accuracy, message };
  }, [scoring, totalBlocks]);
}
