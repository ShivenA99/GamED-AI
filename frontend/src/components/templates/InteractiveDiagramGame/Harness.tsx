'use client';

import InteractiveDiagramGame from './index';
import { InteractiveDiagramBlueprint } from './types';

interface DiagramLabelingHarnessProps {
  blueprint: InteractiveDiagramBlueprint;
  onComplete: (score: number) => void;
  sessionId: string;
  assetUrlOverride?: string;
}

export default function DiagramLabelingHarness({
  blueprint,
  onComplete,
  sessionId,
  assetUrlOverride,
}: DiagramLabelingHarnessProps) {
  const mergedBlueprint = assetUrlOverride
    ? {
        ...blueprint,
        diagram: {
          ...blueprint.diagram,
          assetUrl: assetUrlOverride,
        },
      }
    : blueprint;

  return (
    <InteractiveDiagramGame
      blueprint={mergedBlueprint}
      onComplete={onComplete}
      sessionId={sessionId}
    />
  );
}
