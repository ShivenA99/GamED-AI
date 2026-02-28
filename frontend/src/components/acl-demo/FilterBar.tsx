'use client';

import {
  Domain,
  EducationLevel,
  GameType,
  DOMAIN_LABELS,
  LEVEL_LABELS,
  MECHANIC_LABELS,
} from '@/data/acl-demo/types';

export interface Filters {
  domain: Domain | 'all';
  level: EducationLevel | 'all';
  type: GameType | 'all';
  mechanic: string | 'all';
  blooms: string | 'all';
}

interface FilterBarProps {
  filters: Filters;
  onChange: (filters: Filters) => void;
  availableMechanics: string[];
  availableBlooms: string[];
}

export default function FilterBar({ filters, onChange, availableMechanics, availableBlooms }: FilterBarProps) {
  const update = (key: keyof Filters, value: string) => {
    onChange({ ...filters, [key]: value });
  };

  const activeCount = Object.values(filters).filter(v => v !== 'all').length;

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center gap-3">
        <Select
          label="Domain"
          value={filters.domain}
          onChange={(v) => update('domain', v)}
          options={[
            { value: 'all', label: 'All Domains' },
            ...Object.entries(DOMAIN_LABELS).map(([k, v]) => ({ value: k, label: v })),
          ]}
        />

        <Select
          label="Level"
          value={filters.level}
          onChange={(v) => update('level', v)}
          options={[
            { value: 'all', label: 'All Levels' },
            ...Object.entries(LEVEL_LABELS).map(([k, v]) => ({ value: k, label: v })),
          ]}
        />

        <Select
          label="Type"
          value={filters.type}
          onChange={(v) => update('type', v)}
          options={[
            { value: 'all', label: 'All Types' },
            { value: 'interactive_diagram', label: 'Interactive Diagram' },
            { value: 'algorithm', label: 'Algorithm' },
          ]}
        />

        <Select
          label="Mechanic"
          value={filters.mechanic}
          onChange={(v) => update('mechanic', v)}
          options={[
            { value: 'all', label: 'All Mechanics' },
            ...availableMechanics.map(m => ({ value: m, label: MECHANIC_LABELS[m] || m })),
          ]}
        />

        <Select
          label="Bloom's"
          value={filters.blooms}
          onChange={(v) => update('blooms', v)}
          options={[
            { value: 'all', label: "All Bloom's Levels" },
            ...availableBlooms.map(b => ({ value: b, label: b })),
          ]}
        />

        {activeCount > 0 && (
          <button
            onClick={() => onChange({ domain: 'all', level: 'all', type: 'all', mechanic: 'all', blooms: 'all' })}
            className="px-3 py-1.5 text-sm text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-colors"
          >
            Clear ({activeCount})
          </button>
        )}
      </div>

      {/* Active filter chips */}
      {activeCount > 0 && (
        <div className="flex flex-wrap gap-2">
          {filters.domain !== 'all' && (
            <Chip label={DOMAIN_LABELS[filters.domain as Domain]} onRemove={() => update('domain', 'all')} />
          )}
          {filters.level !== 'all' && (
            <Chip label={LEVEL_LABELS[filters.level as EducationLevel]} onRemove={() => update('level', 'all')} />
          )}
          {filters.type !== 'all' && (
            <Chip label={filters.type === 'interactive_diagram' ? 'Diagram' : 'Algorithm'} onRemove={() => update('type', 'all')} />
          )}
          {filters.mechanic !== 'all' && (
            <Chip label={MECHANIC_LABELS[filters.mechanic] || filters.mechanic} onRemove={() => update('mechanic', 'all')} />
          )}
          {filters.blooms !== 'all' && (
            <Chip label={filters.blooms} onRemove={() => update('blooms', 'all')} />
          )}
        </div>
      )}
    </div>
  );
}

function Select({ label, value, onChange, options }: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  options: { value: string; label: string }[];
}) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      aria-label={label}
      className="px-3 py-2 text-sm bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg text-gray-700 dark:text-gray-300 focus:ring-2 focus:ring-primary-400 focus:border-transparent"
    >
      {options.map(opt => (
        <option key={opt.value} value={opt.value}>{opt.label}</option>
      ))}
    </select>
  );
}

function Chip({ label, onRemove }: { label: string; onRemove: () => void }) {
  return (
    <span className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-medium bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300 rounded-full">
      {label}
      <button onClick={onRemove} className="hover:text-primary-900 dark:hover:text-primary-100">
        <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
          <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
        </svg>
      </button>
    </span>
  );
}
