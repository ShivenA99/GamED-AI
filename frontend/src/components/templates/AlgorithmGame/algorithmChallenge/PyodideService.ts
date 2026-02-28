// ============================================================================
// PyodideService — Singleton wrapper for in-browser Python execution
// ============================================================================
// Lazy-loads Pyodide WASM from CDN on first use. Provides sandboxed Python
// execution with stdout/stderr capture and configurable timeout.
// ============================================================================

export interface ExecutionResult {
  stdout: string;
  stderr: string;
  error?: string;
  executionTimeMs: number;
}

type PyodideInstance = {
  runPythonAsync: (code: string) => Promise<unknown>;
  runPython: (code: string) => unknown;
  globals: { get: (key: string) => unknown };
};

type LoadPyodideFn = (config: { indexURL: string }) => Promise<PyodideInstance>;

const PYODIDE_CDN = 'https://cdn.jsdelivr.net/pyodide/v0.27.3/full/';
const DEFAULT_TIMEOUT_MS = 5000;

class PyodideService {
  private static instance: PyodideService;
  private pyodide: PyodideInstance | null = null;
  private loadingPromise: Promise<PyodideInstance> | null = null;

  private constructor() {}

  static getInstance(): PyodideService {
    if (!PyodideService.instance) {
      PyodideService.instance = new PyodideService();
    }
    return PyodideService.instance;
  }

  get isReady(): boolean {
    return this.pyodide !== null;
  }

  get isLoading(): boolean {
    return this.loadingPromise !== null && this.pyodide === null;
  }

  /** Lazily load Pyodide from CDN. Returns immediately if already loaded. */
  async load(): Promise<void> {
    if (this.pyodide) return;
    if (this.loadingPromise) {
      await this.loadingPromise;
      return;
    }

    this.loadingPromise = this._doLoad();
    try {
      this.pyodide = await this.loadingPromise;
    } finally {
      this.loadingPromise = null;
    }
  }

  private async _doLoad(): Promise<PyodideInstance> {
    // Dynamic import from CDN script
    const script = document.createElement('script');
    script.src = `${PYODIDE_CDN}pyodide.js`;

    await new Promise<void>((resolve, reject) => {
      script.onload = () => resolve();
      script.onerror = () => reject(new Error('Failed to load Pyodide script from CDN'));
      document.head.appendChild(script);
    });

    const loadPyodide = (globalThis as unknown as { loadPyodide: LoadPyodideFn }).loadPyodide;
    if (!loadPyodide) {
      throw new Error('loadPyodide not found on globalThis after script load');
    }

    const pyodide = await loadPyodide({ indexURL: PYODIDE_CDN });
    return pyodide;
  }

  /** Execute arbitrary Python code and capture stdout/stderr. */
  async execute(code: string, timeoutMs = DEFAULT_TIMEOUT_MS): Promise<ExecutionResult> {
    await this.load();
    const py = this.pyodide!;

    const start = performance.now();

    // Set up stdout/stderr capture
    const setupCapture = `
import sys, io
__stdout_capture = io.StringIO()
__stderr_capture = io.StringIO()
sys.stdout = __stdout_capture
sys.stderr = __stderr_capture
`;
    const readCapture = `
sys.stdout = sys.__stdout__
sys.stderr = sys.__stderr__
(__stdout_capture.getvalue(), __stderr_capture.getvalue())
`;

    try {
      const result = await Promise.race([
        (async () => {
          await py.runPythonAsync(setupCapture);
          await py.runPythonAsync(code);
          const captured = await py.runPythonAsync(readCapture);
          return captured;
        })(),
        new Promise<never>((_, reject) =>
          setTimeout(() => reject(new Error('Execution timed out')), timeoutMs),
        ),
      ]);

      const elapsed = performance.now() - start;

      // result is a Pyodide proxy for the tuple (stdout, stderr)
      let stdout = '';
      let stderr = '';
      if (result && typeof result === 'object' && 'toJs' in result) {
        const arr = (result as { toJs: () => [string, string] }).toJs();
        stdout = arr[0] ?? '';
        stderr = arr[1] ?? '';
      }

      return { stdout: stdout.trimEnd(), stderr: stderr.trimEnd(), executionTimeMs: elapsed };
    } catch (err) {
      const elapsed = performance.now() - start;
      // Reset stdout/stderr in case of error
      try {
        py.runPython('sys.stdout = sys.__stdout__; sys.stderr = sys.__stderr__');
      } catch { /* ignore */ }

      const message = err instanceof Error ? err.message : String(err);
      return { stdout: '', stderr: '', error: message, executionTimeMs: elapsed };
    }
  }

  /** Convenience: run a test case (setup + user code + call + print). */
  async runTestCase(
    userCode: string,
    setupCode: string,
    callCode: string,
    printCode: string,
    timeoutMs = DEFAULT_TIMEOUT_MS,
  ): Promise<ExecutionResult> {
    const fullCode = [userCode, setupCode, callCode, printCode].join('\n');
    return this.execute(fullCode, timeoutMs);
  }
}

export default PyodideService;
