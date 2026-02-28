'use client';

import { Label, DistractorLabel } from './types';
import DraggableLabel from './DraggableLabel';

interface LabelTrayProps {
  labels: (Label | DistractorLabel)[];
  draggingLabelId: string | null;
  incorrectLabelId?: string | null;
}

export default function LabelTray({
  labels,
  draggingLabelId,
  incorrectLabelId,
}: LabelTrayProps) {
  if (labels.length === 0) {
    return (
      <div className="p-4 bg-gray-50 rounded-lg text-center">
        <p className="text-gray-500 text-sm">All labels placed!</p>
      </div>
    );
  }

  return (
    <div className="p-4 bg-gray-50 rounded-lg">
      <h3 className="text-sm font-semibold text-gray-600 mb-3">
        Drag labels to the correct positions:
      </h3>
      <div className="flex flex-wrap gap-2">
        {labels.map((label) => (
          <DraggableLabel
            key={label.id}
            id={label.id}
            text={label.text}
            isDragging={draggingLabelId === label.id}
            isIncorrect={incorrectLabelId === label.id}
          />
        ))}
      </div>
    </div>
  );
}
