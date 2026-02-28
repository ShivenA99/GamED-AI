// ============================================================================
// useCombinedPuzzleMachine — Orchestration hook for Combined Puzzle + Code
// ============================================================================
// Manages two independent sub-machines (puzzle + code) and a comparison phase.
// ============================================================================

import { useState, useCallback, useMemo, useRef } from 'react';
import { useGenericConstraintPuzzleMachine } from './useGenericConstraintPuzzleMachine';
import { useAlgorithmBuilderMachine } from './useAlgorithmBuilderMachine';
import { gradeSubmission } from './useAlgorithmBuilderScoring';
import PyodideService from '../algorithmChallenge/PyodideService';
import {
  CombinedPuzzleBlueprint,
  CombinedGamePhase,
  CodeSideState,
  CodePhase,
  TestRunResult,
  CombinedScoring,
  getSerializerForBoardType,
  normalizeForComparison,
} from '../algorithmChallenge/combinedPuzzleTypes';
import { AlgorithmBuilderBlueprint } from '../types';

// ---------------------------------------------------------------------------
// Build a synthetic AlgorithmBuilderBlueprint from the challenge config
// ---------------------------------------------------------------------------

function buildParsonsBlueprint(bp: CombinedPuzzleBlueprint): AlgorithmBuilderBlueprint {
  const ch = bp.algorithmChallenge;
  return {
    algorithmName: bp.title,
    algorithmDescription: bp.description,
    problemDescription: `Implement the algorithm in Python by arranging the code blocks.`,
    language: ch.language,
    correct_order: ch.correctOrder ?? [],
    distractors: ch.distractors ?? [],
    config: ch.parsonsConfig ?? {
      indentation_matters: true,
      max_attempts: null,
      show_line_numbers: true,
      allow_indent_adjustment: true,
    },
    hints: ch.hints,
  };
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export function useCombinedPuzzleMachine(blueprint: CombinedPuzzleBlueprint) {
  const challenge = blueprint.algorithmChallenge;
  const pyodide = useRef(PyodideService.getInstance());

  // ----- Game phase -----
  const [gamePhase, setGamePhase] = useState<CombinedGamePhase>('INTRO');

  // ----- Puzzle side (reused generic machine) -----
  const puzzleMachine = useGenericConstraintPuzzleMachine(blueprint.puzzleBlueprint);

  // ----- Parsons side (reused algorithm builder machine) -----
  const parsonsBlueprint = useMemo(() => buildParsonsBlueprint(blueprint), [blueprint]);
  const parsonsMachine = useAlgorithmBuilderMachine(parsonsBlueprint);

  // ----- Code side state -----
  const [codeSide, setCodeSide] = useState<CodeSideState>({
    phase: 'IDLE',
    activeTab: challenge.mode === 'free_code' ? 'free_code' : 'parsons',
    freeCodeValue: challenge.starterCode ?? '',
    testResults: [],
    passRate: 0,
    codeScore: 0,
    hintTier: 0,
    pyodideReady: pyodide.current.isReady,
    pyodideLoading: false,
    errorMessage: null,
    puzzleCaseOutput: null,
  });

  // ----- Scoring -----
  const [scoring, setScoring] = useState<CombinedScoring>({
    codeScore: 0,
    puzzleScore: 0,
    consistencyBonus: 0,
    totalScore: 0,
  });

  // ----- Actions -----

  const startGame = useCallback(() => {
    setGamePhase('PLAYING');
    puzzleMachine.start();
    if (challenge.mode !== 'free_code') {
      parsonsMachine.startBuilding();
    }
    setCodeSide((prev) => ({ ...prev, phase: challenge.mode === 'free_code' ? 'EDITING' : 'BUILDING' }));
  }, [puzzleMachine, parsonsMachine, challenge.mode]);

  const setActiveTab = useCallback((tab: 'parsons' | 'free_code') => {
    setCodeSide((prev) => ({
      ...prev,
      activeTab: tab,
      phase: tab === 'parsons' ? 'BUILDING' : 'EDITING',
    }));
  }, []);

  const setFreeCode = useCallback((code: string) => {
    setCodeSide((prev) => ({ ...prev, freeCodeValue: code }));
  }, []);

  /** Assemble the user's code from whichever tab is active */
  const getUserCode = useCallback((): string => {
    if (codeSide.activeTab === 'parsons') {
      // Reconstruct code from solution blocks
      return parsonsMachine.state.solutionBlocks
        .map((b) => '    '.repeat(b.indent_level) + b.code)
        .join('\n');
    }
    return codeSide.freeCodeValue;
  }, [codeSide.activeTab, codeSide.freeCodeValue, parsonsMachine.state.solutionBlocks]);

  /** Run all test cases via Pyodide */
  const runCode = useCallback(async () => {
    setCodeSide((prev) => ({ ...prev, phase: 'RUNNING', pyodideLoading: !prev.pyodideReady, errorMessage: null }));

    try {
      await pyodide.current.load();
      setCodeSide((prev) => ({ ...prev, pyodideReady: true, pyodideLoading: false }));

      const userCode = getUserCode();
      const results: TestRunResult[] = [];

      for (const tc of challenge.testCases) {
        const execResult = await pyodide.current.runTestCase(
          userCode,
          tc.setupCode,
          tc.callCode,
          tc.printCode,
        );

        const actualOutput = execResult.stdout.trimEnd();
        const passed =
          normalizeForComparison(actualOutput) === normalizeForComparison(tc.expectedOutput);

        results.push({
          testId: tc.id,
          label: tc.label,
          expectedOutput: tc.expectedOutput,
          actualOutput: execResult.error ? `Error: ${execResult.error}` : actualOutput,
          passed,
          error: execResult.error,
          executionTimeMs: execResult.executionTimeMs,
          isPuzzleCase: tc.isPuzzleCase,
        });
      }

      const passCount = results.filter((r) => r.passed).length;
      const passRate = challenge.testCases.length > 0 ? passCount / challenge.testCases.length : 0;
      const puzzleCaseResult = results.find((r) => r.isPuzzleCase && r.passed);

      setCodeSide((prev) => ({
        ...prev,
        phase: 'RESULTS_SHOWN',
        testResults: results,
        passRate,
        puzzleCaseOutput: puzzleCaseResult?.actualOutput ?? null,
      }));
    } catch (err) {
      setCodeSide((prev) => ({
        ...prev,
        phase: 'IDLE',
        pyodideLoading: false,
        errorMessage: err instanceof Error ? err.message : 'Unknown error loading Pyodide',
      }));
    }
  }, [getUserCode, challenge.testCases]);

  /** Submit code side (lock it in, compute score) */
  const submitCode = useCallback(() => {
    let codeScore = 0;

    if (codeSide.activeTab === 'parsons') {
      // Grade via existing Parsons grading
      const result = gradeSubmission(
        parsonsMachine.state.solutionBlocks,
        parsonsMachine.state.sourceBlocks,
        parsonsBlueprint,
        parsonsMachine.state.scoring.attempts,
        parsonsMachine.state.scoring.hintPenalty,
      );
      codeScore = Math.min(result.score, 300);
    } else {
      // Free code: score proportional to passing tests
      codeScore = Math.round(300 * codeSide.passRate);
    }

    // Apply hint penalty
    const hintPenalty = codeSide.hintTier * 30;
    codeScore = Math.max(codeScore - hintPenalty, 0);

    setCodeSide((prev) => ({
      ...prev,
      phase: 'SUBMITTED',
      codeScore,
    }));

    return codeScore;
  }, [codeSide.activeTab, codeSide.passRate, codeSide.hintTier, parsonsMachine, parsonsBlueprint]);

  /** Use a code hint */
  const useCodeHint = useCallback((tier: number) => {
    setCodeSide((prev) => ({
      ...prev,
      hintTier: Math.max(prev.hintTier, tier),
    }));
  }, []);

  /** Check if both sides are submitted; if so, run comparison */
  const tryComparison = useCallback(() => {
    const puzzleSolved = puzzleMachine.state.phase === 'PUZZLE_SOLVED' ||
                         puzzleMachine.state.phase === 'ALGORITHM_REVEAL' ||
                         puzzleMachine.state.phase === 'COMPLETED';
    const codeSubmitted = codeSide.phase === 'SUBMITTED';

    if (!puzzleSolved || !codeSubmitted) return;

    // Compute puzzle score from machine
    const puzzleScore = puzzleMachine.state.scoring.totalScore;

    // Code score already computed
    const codeScore = codeSide.codeScore;

    // Consistency bonus: compare code output with puzzle state
    let consistencyBonus = 0;
    if (codeSide.puzzleCaseOutput) {
      const serializer = getSerializerForBoardType(blueprint.puzzleBlueprint.boardConfig.boardType);
      const puzzleSerialized = serializer(puzzleMachine.state);
      if (
        normalizeForComparison(codeSide.puzzleCaseOutput) ===
        normalizeForComparison(puzzleSerialized)
      ) {
        consistencyBonus = 100;
      }
    }

    const totalScore = codeScore + puzzleScore + consistencyBonus;

    setScoring({ codeScore, puzzleScore, consistencyBonus, totalScore });
    setGamePhase('COMPARING');
  }, [puzzleMachine.state, codeSide, blueprint.puzzleBlueprint.boardConfig.boardType]);

  /** Complete the game */
  const completeGame = useCallback(() => {
    setGamePhase('COMPLETED');
  }, []);

  /** Reset everything */
  const resetGame = useCallback(() => {
    setGamePhase('INTRO');
    puzzleMachine.reset();
    parsonsMachine.reset();
    setCodeSide({
      phase: 'IDLE',
      activeTab: challenge.mode === 'free_code' ? 'free_code' : 'parsons',
      freeCodeValue: challenge.starterCode ?? '',
      testResults: [],
      passRate: 0,
      codeScore: 0,
      hintTier: 0,
      pyodideReady: pyodide.current.isReady,
      pyodideLoading: false,
      errorMessage: null,
      puzzleCaseOutput: null,
    });
    setScoring({ codeScore: 0, puzzleScore: 0, consistencyBonus: 0, totalScore: 0 });
  }, [puzzleMachine, parsonsMachine, challenge]);

  return {
    // State
    gamePhase,
    codeSide,
    scoring,
    puzzleMachine,
    parsonsMachine,
    parsonsBlueprint,
    blueprint,

    // Actions
    startGame,
    setActiveTab,
    setFreeCode,
    getUserCode,
    runCode,
    submitCode,
    useCodeHint,
    tryComparison,
    completeGame,
    resetGame,
  };
}
