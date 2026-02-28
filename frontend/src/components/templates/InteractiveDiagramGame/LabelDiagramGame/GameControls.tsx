'use client';

interface GameControlsProps {
  showHints: boolean;
  onToggleHints: () => void;
  onReset: () => void;
  hasHints: boolean;
  score: number;
  maxScore: number;
}

export default function GameControls({
  showHints,
  onToggleHints,
  onReset,
  hasHints,
  score,
  maxScore,
}: GameControlsProps) {
  return (
    <div className="flex items-center justify-between p-4 bg-white rounded-lg shadow-sm">
      <div className="flex items-center gap-4">
        {/* Score display */}
        <div className="flex items-center gap-2">
          <span className="text-sm text-gray-500">Score:</span>
          <span className="text-lg font-bold text-primary-600">
            {score} / {maxScore}
          </span>
        </div>

        {/* Progress bar */}
        <div className="w-32 h-2 bg-gray-200 rounded-full overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-primary-500 to-secondary-500 transition-all duration-300"
            style={{ width: `${maxScore > 0 ? (score / maxScore) * 100 : 0}%` }}
          />
        </div>
      </div>

      <div className="flex items-center gap-2">
        {/* Hints toggle */}
        {hasHints && (
          <button
            onClick={onToggleHints}
            className={`
              px-3 py-1.5 rounded-lg text-sm font-medium
              transition-colors duration-200
              flex items-center gap-1.5
              ${
                showHints
                  ? 'bg-yellow-100 text-yellow-700 hover:bg-yellow-200'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }
            `}
          >
            <svg
              className="w-4 h-4"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"
              />
            </svg>
            {showHints ? 'Hide Hints' : 'Show Hints'}
          </button>
        )}

        {/* Reset button */}
        <button
          onClick={onReset}
          className="px-3 py-1.5 bg-gray-100 text-gray-600 rounded-lg text-sm font-medium hover:bg-gray-200 transition-colors duration-200 flex items-center gap-1.5"
        >
          <svg
            className="w-4 h-4"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
            />
          </svg>
          Reset
        </button>
      </div>
    </div>
  );
}
