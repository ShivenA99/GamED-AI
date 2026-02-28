import { useReducer, useCallback, useMemo } from 'react';
import {
  BugHunterBlueprint,
  BugHunterGameState,
  BugHunterAction,
  BugHunterScoringState,
  NormalizedBugHunterBlueprint,
  NormalizedBugDefinition,
  TestExecutionResult,
} from '../types';
import { normalizeBugHunterBlueprint, normalizeBug } from './normalizeBugHunterBlueprint';

const initialScoring: BugHunterScoringState = {
  totalScore: 0,
  bugsFound: 0,
  totalBugs: 0,
  wrongLineClicks: 0,
  wrongFixAttempts: 0,
  hintsUsed: 0,
  perBugScores: [],
  bonuses: [],
};

function createInitialState(bp: NormalizedBugHunterBlueprint): BugHunterGameState {
  const totalBugs = bp.rounds.reduce((sum, r) => sum + r.bugs.length, 0);
  return {
    phase: 'INIT',
    currentBugIndex: 0,
    currentRoundIndex: 0,
    fixedBugIds: [],
    lineStates: {},
    selectedLine: null,
    selectedLines: [],
    scoring: { ...initialScoring, totalBugs },
    hintTier: 0,
    feedbackMessage: null,
    feedbackType: null,
    wrongFixCount: 0,
    currentBugAttempts: 0,
    testResults: [],
    showTestResults: false,
    executionPending: false,
  };
}

function arraysMatch(a: number[], b: number[]): boolean {
  if (a.length !== b.length) return false;
  const sorted1 = [...a].sort((x, y) => x - y);
  const sorted2 = [...b].sort((x, y) => x - y);
  return sorted1.every((v, i) => v === sorted2[i]);
}

function createReducer(bp: NormalizedBugHunterBlueprint) {
  const getCurrentRound = (state: BugHunterGameState) =>
    bp.rounds[state.currentRoundIndex] ?? null;

  const getCurrentBug = (state: BugHunterGameState): NormalizedBugDefinition | null => {
    const round = getCurrentRound(state);
    if (!round) return null;
    const bug = round.bugs[state.currentBugIndex] ?? null;
    return bug ? normalizeBug(bug) : null;
  };

  const getTotalBugsInRound = (roundIndex: number) =>
    bp.rounds[roundIndex]?.bugs.length ?? 0;

  return function reducer(state: BugHunterGameState, action: BugHunterAction): BugHunterGameState {
    switch (action.type) {
      case 'START_HUNTING':
        return { ...state, phase: 'BUG_HUNTING' };

      // Legacy single-line click (backward compat with existing code)
      case 'CLICK_LINE': {
        if (state.phase !== 'BUG_HUNTING') return state;

        const { lineNumber } = action;
        const bug = getCurrentBug(state);
        const round = getCurrentRound(state);
        if (!bug || !round) return state;

        if (state.lineStates[lineNumber] === 'fixed') return state;

        // Check if this line is one of the bug's lines
        if (bug.bugLines.includes(lineNumber)) {
          // Single-line bug: go straight to LINE_SELECTED
          if (bug.bugLines.length === 1) {
            return {
              ...state,
              phase: 'LINE_SELECTED',
              selectedLine: lineNumber,
              selectedLines: [lineNumber],
              lineStates: { ...state.lineStates, [lineNumber]: 'selected' },
              feedbackMessage: null,
              feedbackType: null,
            };
          }
          // Multi-line bug: add to selection (use SELECT_LINE instead)
          return {
            ...state,
            selectedLines: state.selectedLines.includes(lineNumber)
              ? state.selectedLines.filter((l) => l !== lineNumber)
              : [...state.selectedLines, lineNumber],
            lineStates: {
              ...state.lineStates,
              [lineNumber]: state.selectedLines.includes(lineNumber) ? 'default' : 'selected',
            },
            feedbackMessage: null,
            feedbackType: null,
          };
        }

        // Red herring or wrong line
        const rh = round.redHerrings.find((r) => r.lineNumber === lineNumber);
        return {
          ...state,
          lineStates: { ...state.lineStates, [lineNumber]: 'wrong_click' },
          feedbackMessage: rh
            ? rh.feedback
            : 'This line is correct. Look more carefully at the algorithm logic.',
          feedbackType: 'info',
          scoring: {
            ...state.scoring,
            totalScore: state.scoring.totalScore - 10,
            wrongLineClicks: state.scoring.wrongLineClicks + 1,
          },
          currentBugAttempts: state.currentBugAttempts + 1,
        };
      }

      // Multi-line selection with shift support
      case 'SELECT_LINE': {
        if (state.phase !== 'BUG_HUNTING') return state;

        const { lineNumber, multiSelect } = action;
        if (state.lineStates[lineNumber] === 'fixed') return state;

        let newSelectedLines: number[];
        const newLineStates = { ...state.lineStates };

        if (multiSelect && state.selectedLines.length > 0) {
          // Shift+click: select range from last selected to clicked
          const lastSelected = state.selectedLines[state.selectedLines.length - 1];
          const start = Math.min(lastSelected, lineNumber);
          const end = Math.max(lastSelected, lineNumber);
          const rangeLines: number[] = [];
          for (let i = start; i <= end; i++) {
            if (newLineStates[i] !== 'fixed') {
              rangeLines.push(i);
            }
          }
          // Merge with existing selection
          const merged = new Set([...state.selectedLines, ...rangeLines]);
          newSelectedLines = Array.from(merged).sort((a, b) => a - b);
        } else {
          // Regular click: toggle single line
          if (state.selectedLines.includes(lineNumber)) {
            newSelectedLines = state.selectedLines.filter((l) => l !== lineNumber);
            newLineStates[lineNumber] = 'default';
          } else {
            newSelectedLines = [...state.selectedLines, lineNumber].sort((a, b) => a - b);
          }
        }

        // Update line states
        for (const ln of newSelectedLines) {
          newLineStates[ln] = 'selected';
        }
        // Clear deselected lines
        for (const ln of state.selectedLines) {
          if (!newSelectedLines.includes(ln) && newLineStates[ln] === 'selected') {
            newLineStates[ln] = 'default';
          }
        }

        return {
          ...state,
          selectedLines: newSelectedLines,
          selectedLine: newSelectedLines.length === 1 ? newSelectedLines[0] : (newSelectedLines[0] ?? null),
          lineStates: newLineStates,
          feedbackMessage: null,
          feedbackType: null,
        };
      }

      // Confirm multi-line selection
      case 'CONFIRM_SELECTION': {
        if (state.phase !== 'BUG_HUNTING') return state;

        const bug = getCurrentBug(state);
        if (!bug) return state;

        if (arraysMatch(state.selectedLines, bug.bugLines)) {
          return {
            ...state,
            phase: 'LINE_SELECTED',
            feedbackMessage: null,
            feedbackType: null,
          };
        }

        // Wrong selection
        return {
          ...state,
          feedbackMessage: 'Those aren\'t the right lines. Try a different selection.',
          feedbackType: 'info',
          scoring: {
            ...state.scoring,
            totalScore: state.scoring.totalScore - 10,
            wrongLineClicks: state.scoring.wrongLineClicks + 1,
          },
          currentBugAttempts: state.currentBugAttempts + 1,
        };
      }

      case 'DISMISS_FEEDBACK': {
        const resetLines = { ...state.lineStates };
        for (const [line, ls] of Object.entries(resetLines)) {
          if (ls === 'wrong_click') resetLines[Number(line)] = 'default';
        }
        return {
          ...state,
          lineStates: resetLines,
          feedbackMessage: null,
          feedbackType: null,
        };
      }

      // MCQ fix submission (existing)
      case 'SUBMIT_FIX': {
        if (state.phase !== 'LINE_SELECTED' && state.phase !== 'WRONG_FIX') return state;

        const bug = getCurrentBug(state);
        if (!bug || !bug.fixOptions) return state;

        const fix = bug.fixOptions.find((f) => f.id === action.fixId);
        if (!fix) return state;

        if (fix.isCorrect) {
          const attemptNum = state.wrongFixCount + 1;
          const basePoints = attemptNum === 1 ? 150 : attemptNum === 2 ? 100 : 50;
          const diffMult = bug.difficulty === 1 ? 1.0 : bug.difficulty === 2 ? 1.5 : 2.0;
          const hintPenalty =
            state.hintTier === 0 ? 0 :
            state.hintTier === 1 ? 0.15 :
            state.hintTier === 2 ? 0.30 : 0.50;
          const points = Math.round(basePoints * diffMult * (1 - hintPenalty));

          const newFixedIds = [...state.fixedBugIds, bug.bugId];
          const round = getCurrentRound(state);
          const allBugsInRound = round ? round.bugs.length : 0;

          // Mark all bug lines as fixed
          const newLineStates = { ...state.lineStates };
          for (const ln of bug.bugLines) {
            newLineStates[ln] = 'fixed';
          }

          return {
            ...state,
            phase: 'BUG_FIXED',
            fixedBugIds: newFixedIds,
            lineStates: newLineStates,
            feedbackMessage: fix.feedback,
            feedbackType: 'success',
            scoring: {
              ...state.scoring,
              totalScore: state.scoring.totalScore + points,
              bugsFound: state.scoring.bugsFound + 1,
              perBugScores: [
                ...state.scoring.perBugScores,
                {
                  bugId: bug.bugId,
                  points,
                  attempts: state.wrongFixCount + 1,
                  hintsUsed: state.hintTier,
                },
              ],
            },
            wrongFixCount: 0,
          };
        }

        return {
          ...state,
          phase: 'WRONG_FIX',
          feedbackMessage: fix.feedback,
          feedbackType: 'error',
          wrongFixCount: state.wrongFixCount + 1,
          scoring: {
            ...state.scoring,
            totalScore: state.scoring.totalScore - 20,
            wrongFixAttempts: state.scoring.wrongFixAttempts + 1,
          },
        };
      }

      // Free-text fix submission — just sets pending, actual execution is outside reducer
      case 'SUBMIT_FREE_TEXT': {
        if (state.phase !== 'LINE_SELECTED' && state.phase !== 'WRONG_FIX') return state;
        return {
          ...state,
          executionPending: true,
          showTestResults: false,
          testResults: [],
        };
      }

      case 'SET_EXECUTION_PENDING': {
        return { ...state, executionPending: action.pending };
      }

      // Test results from execution
      case 'SET_TEST_RESULTS': {
        const { results } = action;
        const allPassed = results.every((r) => r.passed);
        const bug = getCurrentBug(state);

        if (allPassed && bug) {
          // Fix is correct
          const attemptNum = state.wrongFixCount + 1;
          const basePoints = attemptNum === 1 ? 200 : attemptNum === 2 ? 130 : 70;
          const diffMult = bug.difficulty === 1 ? 1.0 : bug.difficulty === 2 ? 1.5 : 2.0;
          const hintPenalty =
            state.hintTier === 0 ? 0 :
            state.hintTier === 1 ? 0.15 :
            state.hintTier === 2 ? 0.30 : 0.50;

          // Partial credit: proportion of tests passed
          const passRate = results.filter((r) => r.passed).length / results.length;
          const points = Math.round(basePoints * diffMult * (1 - hintPenalty) * passRate);

          const newFixedIds = [...state.fixedBugIds, bug.bugId];
          const newLineStates = { ...state.lineStates };
          for (const ln of bug.bugLines) {
            newLineStates[ln] = 'fixed';
          }

          return {
            ...state,
            phase: 'BUG_FIXED',
            fixedBugIds: newFixedIds,
            lineStates: newLineStates,
            testResults: results,
            showTestResults: true,
            executionPending: false,
            feedbackMessage: 'All tests pass! Great fix.',
            feedbackType: 'success',
            scoring: {
              ...state.scoring,
              totalScore: state.scoring.totalScore + points,
              bugsFound: state.scoring.bugsFound + 1,
              perBugScores: [
                ...state.scoring.perBugScores,
                {
                  bugId: bug.bugId,
                  points,
                  attempts: state.wrongFixCount + 1,
                  hintsUsed: state.hintTier,
                },
              ],
            },
            wrongFixCount: 0,
          };
        }

        // Some tests failed
        const passedCount = results.filter((r) => r.passed).length;
        return {
          ...state,
          phase: 'WRONG_FIX',
          testResults: results,
          showTestResults: true,
          executionPending: false,
          feedbackMessage: `${passedCount}/${results.length} tests passed. Review the failures and try again.`,
          feedbackType: 'error',
          wrongFixCount: state.wrongFixCount + 1,
          scoring: {
            ...state.scoring,
            totalScore: state.scoring.totalScore - 20,
            wrongFixAttempts: state.scoring.wrongFixAttempts + 1,
          },
        };
      }

      case 'DISMISS_TEST_RESULTS': {
        return {
          ...state,
          showTestResults: false,
          testResults: [],
        };
      }

      case 'ADVANCE_AFTER_FIX': {
        const round = getCurrentRound(state);
        if (!round) return state;

        const nextBugIndex = state.currentBugIndex + 1;
        const allBugsInRoundFixed = nextBugIndex >= round.bugs.length;

        if (allBugsInRoundFixed) {
          const isLastRound = state.currentRoundIndex >= bp.rounds.length - 1;
          if (isLastRound) {
            // All rounds done — go to verification
            return {
              ...state,
              phase: 'VERIFICATION',
              selectedLine: null,
              selectedLines: [],
              feedbackMessage: null,
              feedbackType: null,
              showTestResults: false,
              testResults: [],
            };
          }
          // More rounds — prompt advance
          return {
            ...state,
            phase: 'BUG_FIXED', // stay in BUG_FIXED, BugHunterGame will show "Next Round" button
            feedbackMessage: 'Round complete! Ready for the next challenge.',
            feedbackType: 'success',
          };
        }

        return {
          ...state,
          phase: 'BUG_HUNTING',
          currentBugIndex: nextBugIndex,
          selectedLine: null,
          selectedLines: [],
          feedbackMessage: null,
          feedbackType: null,
          hintTier: 0,
          currentBugAttempts: 0,
          showTestResults: false,
          testResults: [],
        };
      }

      case 'ADVANCE_ROUND': {
        const nextRoundIndex = state.currentRoundIndex + 1;
        if (nextRoundIndex >= bp.rounds.length) {
          // All rounds done
          return {
            ...state,
            phase: 'VERIFICATION',
            selectedLine: null,
            selectedLines: [],
            feedbackMessage: null,
            feedbackType: null,
          };
        }

        return {
          ...state,
          phase: 'READING_CODE',
          currentRoundIndex: nextRoundIndex,
          currentBugIndex: 0,
          fixedBugIds: [],  // Clear per-round — bug IDs are scoped to a round
          selectedLine: null,
          selectedLines: [],
          lineStates: {},
          feedbackMessage: null,
          feedbackType: null,
          hintTier: 0,
          wrongFixCount: 0,
          currentBugAttempts: 0,
          showTestResults: false,
          testResults: [],
        };
      }

      case 'USE_HINT': {
        const newTier = Math.max(state.hintTier, action.tier);
        const isNewHint = newTier > state.hintTier;
        return {
          ...state,
          hintTier: newTier,
          scoring: {
            ...state.scoring,
            hintsUsed: state.scoring.hintsUsed + (isNewHint ? 1 : 0),
          },
        };
      }

      case 'START_VERIFICATION': {
        const totalBugsAllRounds = bp.rounds.reduce((sum, r) => sum + r.bugs.length, 0);
        const bonuses: { type: string; points: number }[] = [];
        if (state.scoring.bugsFound >= totalBugsAllRounds) {
          bonuses.push({ type: 'All bugs found', points: 100 });
        }
        if (state.scoring.wrongLineClicks === 0) {
          bonuses.push({ type: 'No wrong clicks', points: 50 });
        }
        if (state.scoring.hintsUsed === 0) {
          bonuses.push({ type: 'Clean sweep', points: 75 });
        }
        const bonusTotal = bonuses.reduce((s, b) => s + b.points, 0);

        return {
          ...state,
          phase: 'VERIFICATION',
          scoring: {
            ...state.scoring,
            totalScore: state.scoring.totalScore + bonusTotal,
            bonuses,
          },
        };
      }

      case 'COMPLETE':
        return { ...state, phase: 'COMPLETED' };

      case 'RESET':
        return createInitialState(bp);

      default:
        return state;
    }
  };
}

export function useBugHunterMachine(blueprint: BugHunterBlueprint) {
  const normalized = useMemo(() => normalizeBugHunterBlueprint(blueprint), [blueprint]);

  const reducer = useMemo(() => createReducer(normalized), [normalized]);
  const initializer = useCallback(
    () => createInitialState(normalized),
    [normalized],
  );

  const [state, dispatch] = useReducer(reducer, undefined, initializer);

  const currentRound = normalized.rounds[state.currentRoundIndex] ?? null;
  const currentBug = currentRound
    ? (currentRound.bugs[state.currentBugIndex] ? normalizeBug(currentRound.bugs[state.currentBugIndex]) : null)
    : null;

  const startHunting = useCallback(() => {
    dispatch({ type: 'START_HUNTING' });
  }, []);

  const clickLine = useCallback((lineNumber: number) => {
    dispatch({ type: 'CLICK_LINE', lineNumber });
  }, []);

  const selectLine = useCallback((lineNumber: number, multiSelect: boolean) => {
    dispatch({ type: 'SELECT_LINE', lineNumber, multiSelect });
  }, []);

  const confirmSelection = useCallback(() => {
    dispatch({ type: 'CONFIRM_SELECTION' });
  }, []);

  const dismissFeedback = useCallback(() => {
    dispatch({ type: 'DISMISS_FEEDBACK' });
  }, []);

  const submitFix = useCallback((fixId: string) => {
    dispatch({ type: 'SUBMIT_FIX', fixId });
  }, []);

  const submitFreeText = useCallback((code: string) => {
    dispatch({ type: 'SUBMIT_FREE_TEXT', code });
  }, []);

  const setTestResults = useCallback((results: TestExecutionResult[]) => {
    dispatch({ type: 'SET_TEST_RESULTS', results });
  }, []);

  const setExecutionPending = useCallback((pending: boolean) => {
    dispatch({ type: 'SET_EXECUTION_PENDING', pending });
  }, []);

  const dismissTestResults = useCallback(() => {
    dispatch({ type: 'DISMISS_TEST_RESULTS' });
  }, []);

  const advanceAfterFix = useCallback(() => {
    dispatch({ type: 'ADVANCE_AFTER_FIX' });
  }, []);

  const advanceRound = useCallback(() => {
    dispatch({ type: 'ADVANCE_ROUND' });
  }, []);

  const useHint = useCallback((tier: number) => {
    dispatch({ type: 'USE_HINT', tier });
  }, []);

  const startVerification = useCallback(() => {
    dispatch({ type: 'START_VERIFICATION' });
  }, []);

  const complete = useCallback(() => {
    dispatch({ type: 'COMPLETE' });
  }, []);

  const reset = useCallback(() => {
    dispatch({ type: 'RESET' });
  }, []);

  return {
    state,
    dispatch,
    normalized,
    currentRound,
    currentBug,
    startHunting,
    clickLine,
    selectLine,
    confirmSelection,
    dismissFeedback,
    submitFix,
    submitFreeText,
    setTestResults,
    setExecutionPending,
    dismissTestResults,
    advanceAfterFix,
    advanceRound,
    useHint,
    startVerification,
    complete,
    reset,
  };
}
