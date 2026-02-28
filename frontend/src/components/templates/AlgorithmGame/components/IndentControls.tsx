'use client';

interface IndentControlsProps {
  indentLevel: number;
  maxIndent?: number;
  onChange: (level: number) => void;
  disabled?: boolean;
  theme?: 'dark' | 'light';
}

export default function IndentControls({
  indentLevel,
  maxIndent = 3,
  onChange,
  disabled = false,
  theme = 'dark',
}: IndentControlsProps) {
  const isDark = theme === 'dark';

  return (
    <div className="flex items-center gap-0.5" onClick={(e) => e.stopPropagation()}>
      <button
        onPointerDown={(e) => e.stopPropagation()}
        onClick={(e) => {
          e.stopPropagation();
          if (indentLevel > 0) onChange(indentLevel - 1);
        }}
        disabled={disabled || indentLevel <= 0}
        className={`w-6 h-6 flex items-center justify-center rounded text-xs font-bold transition-colors ${
          disabled || indentLevel <= 0
            ? isDark
              ? 'text-gray-600 cursor-not-allowed'
              : 'text-gray-300 cursor-not-allowed'
            : isDark
              ? 'text-gray-400 hover:text-white hover:bg-gray-600'
              : 'text-gray-500 hover:text-gray-900 hover:bg-gray-200'
        }`}
        title="Decrease indent (Shift+Tab)"
      >
        {'\u2190'}
      </button>
      <span
        className={`text-[10px] w-3 text-center font-mono ${isDark ? 'text-gray-500' : 'text-gray-400'}`}
      >
        {indentLevel}
      </span>
      <button
        onPointerDown={(e) => e.stopPropagation()}
        onClick={(e) => {
          e.stopPropagation();
          if (indentLevel < maxIndent) onChange(indentLevel + 1);
        }}
        disabled={disabled || indentLevel >= maxIndent}
        className={`w-6 h-6 flex items-center justify-center rounded text-xs font-bold transition-colors ${
          disabled || indentLevel >= maxIndent
            ? isDark
              ? 'text-gray-600 cursor-not-allowed'
              : 'text-gray-300 cursor-not-allowed'
            : isDark
              ? 'text-gray-400 hover:text-white hover:bg-gray-600'
              : 'text-gray-500 hover:text-gray-900 hover:bg-gray-200'
        }`}
        title="Increase indent (Tab)"
      >
        {'\u2192'}
      </button>
    </div>
  );
}
