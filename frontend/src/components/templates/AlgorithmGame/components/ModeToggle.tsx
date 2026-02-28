'use client';

interface ModeToggleProps {
  mode: 'learn' | 'test';
  onToggle: (mode: 'learn' | 'test') => void;
  disabled?: boolean;
}

export default function ModeToggle({ mode, onToggle, disabled = false }: ModeToggleProps) {
  return (
    <div className="flex items-center gap-1 rounded-lg bg-muted p-1">
      <button
        onClick={() => onToggle('learn')}
        disabled={disabled}
        className={`px-3 py-1.5 text-sm font-medium rounded-md transition-all ${
          mode === 'learn'
            ? 'bg-primary text-primary-foreground shadow-sm'
            : 'text-muted-foreground hover:text-foreground'
        } ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
      >
        Learn
      </button>
      <button
        onClick={() => onToggle('test')}
        disabled={disabled}
        className={`px-3 py-1.5 text-sm font-medium rounded-md transition-all ${
          mode === 'test'
            ? 'bg-primary text-primary-foreground shadow-sm'
            : 'text-muted-foreground hover:text-foreground'
        } ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
      >
        Test
      </button>
    </div>
  );
}
