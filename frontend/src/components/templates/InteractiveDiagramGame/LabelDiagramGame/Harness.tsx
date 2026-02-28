'use client';

import LabelDiagramGame from './index';
import { LabelDiagramBlueprint } from './types';

interface DiagramLabelingHarnessProps {
  blueprint: LabelDiagramBlueprint;
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
    <LabelDiagramGame
      blueprint={mergedBlueprint}
      onComplete={onComplete}
      sessionId={sessionId}
    />
  );
}
