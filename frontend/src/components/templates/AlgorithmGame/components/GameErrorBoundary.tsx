'use client';

import React from 'react';

interface GameErrorBoundaryProps {
  children: React.ReactNode;
  sceneName?: string;
  gameType?: string;
  onSkipScene?: () => void;
  onRetry?: () => void;
}

interface GameErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

/**
 * Error Boundary for Algorithm Game scenes.
 *
 * Catches runtime errors caused by malformed LLM-generated data
 * and displays a friendly fallback UI with retry/skip options
 * instead of a white screen crash.
 */
export class GameErrorBoundary extends React.Component<GameErrorBoundaryProps, GameErrorBoundaryState> {
  constructor(props: GameErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): GameErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error(
      `[GameErrorBoundary] ${this.props.gameType || 'unknown'} scene "${this.props.sceneName || 'unknown'}" crashed:`,
      error,
      errorInfo,
    );
  }

  handleRetry = () => {
    this.setState({ hasError: false, error: null });
    this.props.onRetry?.();
  };

  render() {
    if (this.state.hasError) {
      return (
        <div
          className="rounded-xl p-8 text-center bg-red-900/20 border border-red-800/50"
          role="alert"
          aria-live="assertive"
        >
          <div className="text-4xl mb-4" aria-hidden="true">&#x26A0;&#xFE0F;</div>
          <h3 className="text-lg font-semibold mb-2 text-red-300">
            Scene Failed to Load
          </h3>
          <p className="text-sm mb-1 text-gray-400">
            {this.props.sceneName && `Scene: ${this.props.sceneName}`}
            {this.props.gameType && ` (${this.props.gameType.replace(/_/g, ' ')})`}
          </p>
          {this.state.error && (
            <details className="mb-6 text-left max-w-md mx-auto">
              <summary className="cursor-pointer text-red-400/70 text-xs">
                Error details
              </summary>
              <pre className="mt-2 p-2 bg-red-900/30 rounded text-xs overflow-auto max-h-32 text-red-400/70 font-mono">
                {this.state.error.message}
              </pre>
            </details>
          )}
          <div className="flex gap-3 justify-center">
            <button
              onClick={this.handleRetry}
              className="px-4 py-2 rounded-lg text-sm font-medium transition-colors bg-blue-600 hover:bg-blue-500 text-white"
            >
              Retry
            </button>
            {this.props.onSkipScene && (
              <button
                onClick={this.props.onSkipScene}
                className="px-4 py-2 rounded-lg text-sm font-medium transition-colors bg-gray-700 hover:bg-gray-600 text-gray-300"
              >
                Skip Scene
              </button>
            )}
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

export default GameErrorBoundary;
