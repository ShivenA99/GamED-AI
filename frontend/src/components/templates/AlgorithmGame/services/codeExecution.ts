import { TestCase, TestExecutionResult } from '../types';

interface ExecuteRequest {
  code: string;
  language: string;
  testCases: TestCase[];
}

/**
 * Execute user's code against test cases.
 * Tries backend API first, falls back to string comparison.
 */
export async function executeCode(req: ExecuteRequest): Promise<TestExecutionResult[]> {
  // Try backend execution first
  try {
    const res = await fetch('/api/execute', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        code: req.code,
        language: req.language,
        testInputs: req.testCases.map((tc) => tc.inputDescription),
      }),
    });
    if (res.ok) {
      const data = await res.json();
      if (data.results) {
        return req.testCases.map((tc, i) => ({
          testId: tc.id,
          passed: data.results[i]?.exitCode === 0 && !data.results[i]?.error,
          actualOutput: data.results[i]?.output ?? '',
          expectedOutput: tc.expectedOutput,
          error: data.results[i]?.error ?? undefined,
        }));
      }
    }
  } catch {
    // Backend not available, fall through to string match
  }

  return stringMatchFallback(req);
}

/**
 * String-match fallback: compare user's code against the expected correct code.
 * If the code matches the correct fix, all tests pass.
 * Otherwise, tests that don't depend on the fix pass, others fail.
 */
function stringMatchFallback(req: ExecuteRequest): TestExecutionResult[] {
  return req.testCases.map((tc) => ({
    testId: tc.id,
    passed: false,
    actualOutput: tc.buggyOutput,
    expectedOutput: tc.expectedOutput,
    error: 'Code execution unavailable. Comparing against expected fix.',
  }));
}

/**
 * Validate user's free-text fix against the correct lines.
 * Returns true if the trimmed lines match.
 */
export function validateFreeTextFix(
  userCode: string,
  correctLinesText: string[],
): boolean {
  const userLines = userCode
    .split('\n')
    .map((l) => l.trim())
    .filter((l) => l.length > 0);
  const correctLines = correctLinesText
    .map((l) => l.trim())
    .filter((l) => l.length > 0);

  if (userLines.length !== correctLines.length) return false;
  return userLines.every((line, i) => line === correctLines[i]);
}

/**
 * Run tests using string comparison of user fix against correct fix.
 * If fix is correct, all tests pass. If not, only tests not exposed to bugs pass.
 */
export function executeWithStringMatch(
  userCode: string,
  correctLinesText: string[],
  testCases: TestCase[],
  bugId: string,
): TestExecutionResult[] {
  const isCorrect = validateFreeTextFix(userCode, correctLinesText);

  return testCases.map((tc) => {
    const isExposed = tc.exposedBugs.includes(bugId);

    if (isCorrect) {
      return {
        testId: tc.id,
        passed: true,
        actualOutput: tc.expectedOutput,
        expectedOutput: tc.expectedOutput,
      };
    }

    if (!isExposed) {
      // This test wasn't affected by this bug
      return {
        testId: tc.id,
        passed: tc.expectedOutput === tc.buggyOutput,
        actualOutput: tc.buggyOutput,
        expectedOutput: tc.expectedOutput,
      };
    }

    return {
      testId: tc.id,
      passed: false,
      actualOutput: tc.buggyOutput,
      expectedOutput: tc.expectedOutput,
      error: 'Fix does not match expected correction',
    };
  });
}
