'use client';

import { ComplexityChallenge, CodeSection } from '../types';

interface ComplexityCodePanelProps {
  challenge: ComplexityChallenge;
  selectedSection: string | null;
  onSelectSection?: (sectionId: string) => void;
  theme?: 'dark' | 'light';
  showFeedback?: boolean;
  isCorrect?: boolean | null;
}

export default function ComplexityCodePanel({
  challenge,
  selectedSection,
  onSelectSection,
  theme = 'dark',
  showFeedback = false,
  isCorrect,
}: ComplexityCodePanelProps) {
  const isDark = theme === 'dark';
  const lines = (challenge.code ?? '').split('\n');
  const sections = challenge.codeSections ?? [];

  const getSectionForLine = (lineNum: number): CodeSection | undefined => {
    return sections.find(
      (s) => lineNum >= s.startLine && lineNum <= s.endLine,
    );
  };

  const getLineBackground = (lineNum: number): string => {
    const section = getSectionForLine(lineNum);
    if (!section) return '';

    const isSelected = selectedSection === section.sectionId;
    const isBottleneck = section.isBottleneck;

    if (showFeedback && isSelected) {
      if (isBottleneck) {
        return isDark ? 'bg-green-900/30' : 'bg-green-100';
      }
      return isDark ? 'bg-red-900/30' : 'bg-red-100';
    }

    if (isSelected) {
      return isDark ? 'bg-blue-900/40' : 'bg-blue-100';
    }

    return '';
  };

  const isBottleneckType = challenge.type === 'find_bottleneck';

  return (
    <div className={`rounded-lg border overflow-hidden ${isDark ? 'border-gray-700 bg-gray-900' : 'border-gray-200 bg-white'}`}>
      <div className={`px-3 py-2 border-b text-xs font-medium ${isDark ? 'border-gray-700 bg-gray-800 text-gray-400' : 'border-gray-200 bg-gray-50 text-gray-500'}`}>
        {challenge.language ?? 'python'}
        {isBottleneckType && (
          <span className={`ml-2 ${isDark ? 'text-blue-400' : 'text-blue-600'}`}>
            — Click a section to identify the bottleneck
          </span>
        )}
      </div>

      <div className="overflow-x-auto">
        <pre className="text-sm leading-relaxed">
          <code>
            {lines.map((line, i) => {
              const lineNum = i + 1;
              const section = getSectionForLine(lineNum);
              const bgClass = getLineBackground(lineNum);
              const isClickable = isBottleneckType && !!section && !showFeedback;

              return (
                <div
                  key={i}
                  className={`flex ${bgClass} ${
                    isClickable ? 'cursor-pointer hover:opacity-80' : ''
                  } transition-colors`}
                  onClick={
                    isClickable && section
                      ? () => onSelectSection?.(section.sectionId)
                      : undefined
                  }
                >
                  <span
                    className={`select-none w-10 text-right pr-3 flex-shrink-0 ${
                      isDark ? 'text-gray-600' : 'text-gray-400'
                    }`}
                  >
                    {lineNum}
                  </span>
                  <span className={isDark ? 'text-gray-200' : 'text-gray-800'}>
                    {line || ' '}
                  </span>
                  {section && lineNum === section.startLine && (
                    <span
                      className={`ml-4 text-xs px-2 py-0.5 rounded ${
                        selectedSection === section.sectionId
                          ? isDark
                            ? 'bg-blue-800 text-blue-200'
                            : 'bg-blue-200 text-blue-800'
                          : isDark
                            ? 'bg-gray-700 text-gray-400'
                            : 'bg-gray-200 text-gray-500'
                      }`}
                    >
                      {section.label}
                      {showFeedback && (
                        <span className="ml-1">
                          [{section.complexity}]
                        </span>
                      )}
                    </span>
                  )}
                </div>
              );
            })}
          </code>
        </pre>
      </div>

      {showFeedback && isBottleneckType && (
        <div className={`px-3 py-2 border-t text-sm ${isDark ? 'border-gray-700' : 'border-gray-200'}`}>
          {isCorrect ? (
            <span className={isDark ? 'text-green-400' : 'text-green-600'}>
              Correct! You identified the bottleneck section.
            </span>
          ) : (
            <span className={isDark ? 'text-red-400' : 'text-red-600'}>
              The bottleneck is: {sections.find((s) => s.isBottleneck)?.label ?? 'unknown'} ({sections.find((s) => s.isBottleneck)?.complexity})
            </span>
          )}
        </div>
      )}
    </div>
  );
}
