'use client';

import React from 'react';
import { InteractionMode } from './types';

interface MechanicConfigErrorProps {
  mechanic: InteractionMode;
}

const MECHANIC_LABELS: Record<string, string> = {
  sorting_categories: 'Sorting Categories',
  memory_match: 'Memory Match',
  branching_scenario: 'Branching Scenario',
  compare_contrast: 'Compare & Contrast',
  sequencing: 'Sequencing',
  description_matching: 'Description Matching',
  trace_path: 'Trace Path',
  click_to_identify: 'Click to Identify',
  hierarchical: 'Hierarchical',
  timed_challenge: 'Timed Challenge',
};

/**
 * Error component shown when a mechanic's required configuration is missing.
 * Replaces the silent drag_drop fallback (G-09).
 */
export default function MechanicConfigError({ mechanic }: MechanicConfigErrorProps) {
  const label = MECHANIC_LABELS[mechanic] || mechanic.replace(/_/g, ' ');

  return (
    <div className="p-6 bg-amber-50 border border-amber-200 rounded-lg text-center">
      <div className="text-amber-600 text-3xl mb-3">&#9888;</div>
      <h3 className="text-lg font-semibold text-amber-800 mb-2">
        {label} Configuration Missing
      </h3>
      <p className="text-sm text-amber-700 max-w-md mx-auto">
        This game mechanic requires additional configuration that was not generated
        by the pipeline. The game may need to be regenerated with the correct settings.
      </p>
    </div>
  );
}
