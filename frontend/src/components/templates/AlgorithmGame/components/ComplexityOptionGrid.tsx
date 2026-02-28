'use client';

interface ComplexityOptionGridProps {
  options: string[];
  selectedAnswer: string | null;
  onSelect: (answer: string) => void;
  disabled?: boolean;
  correctAnswer?: string | null;
  showFeedback?: boolean;
  theme?: 'dark' | 'light';
}

export default function ComplexityOptionGrid({
  options,
  selectedAnswer,
  onSelect,
  disabled = false,
  correctAnswer = null,
  showFeedback = false,
  theme = 'dark',
}: ComplexityOptionGridProps) {
  const isDark = theme === 'dark';

  const getOptionStyle = (opt: string): string => {
    const isSelected = selectedAnswer === opt;

    if (showFeedback && correctAnswer) {
      if (opt === correctAnswer) {
        return isDark
          ? 'bg-green-900/40 border-green-500 text-green-300 ring-2 ring-green-500/50'
          : 'bg-green-50 border-green-500 text-green-700 ring-2 ring-green-500/50';
      }
      if (isSelected && opt !== correctAnswer) {
        return isDark
          ? 'bg-red-900/40 border-red-500 text-red-300 ring-2 ring-red-500/50'
          : 'bg-red-50 border-red-500 text-red-700 ring-2 ring-red-500/50';
      }
      return isDark
        ? 'bg-gray-800/50 border-gray-700 text-gray-500'
        : 'bg-gray-50 border-gray-200 text-gray-400';
    }

    if (isSelected) {
      return isDark
        ? 'bg-blue-900/40 border-blue-500 text-blue-200 ring-2 ring-blue-500/50'
        : 'bg-blue-50 border-blue-500 text-blue-700 ring-2 ring-blue-500/50';
    }

    return isDark
      ? 'bg-gray-800 border-gray-600 text-gray-200 hover:border-blue-500 hover:bg-gray-700'
      : 'bg-white border-gray-300 text-gray-800 hover:border-blue-500 hover:bg-blue-50';
  };

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
      {options.map((opt) => (
        <button
          key={opt}
          onClick={() => !disabled && onSelect(opt)}
          disabled={disabled}
          className={`px-4 py-3 rounded-lg border-2 font-mono text-base font-semibold
            transition-all ${getOptionStyle(opt)} ${
            disabled ? 'cursor-default' : 'cursor-pointer'
          }`}
        >
          {opt}
        </button>
      ))}
    </div>
  );
}
