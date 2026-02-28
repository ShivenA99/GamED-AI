'use client';

import { useDroppable } from '@dnd-kit/core';
import { Zone, PlacedLabel } from './types';

interface DropZoneProps {
  zone: Zone;
  placedLabel?: PlacedLabel & { text: string };
  showHint?: boolean;
  hintText?: string;
  isHighlighted?: boolean;
}

export default function DropZone({
  zone,
  placedLabel,
  showHint,
  hintText,
  isHighlighted,
}: DropZoneProps) {
  const { isOver, setNodeRef } = useDroppable({
    id: zone.id,
  });

  const size = zone.radius * 2;

  return (
    <div
      ref={setNodeRef}
      className="absolute transform -translate-x-1/2 -translate-y-1/2"
      style={{
        left: `${zone.x}%`,
        top: `${zone.y}%`,
        width: `${size}%`,
        minWidth: '60px',
        minHeight: '36px',
      }}
    >
      {/* Drop zone visual */}
      <div
        className={`
          w-full h-full rounded-lg border-2 border-dashed
          flex items-center justify-center
          transition-all duration-200
          ${
            placedLabel
              ? 'bg-green-100 border-green-500'
              : isOver
              ? 'bg-primary-100 border-primary-500 scale-110'
              : isHighlighted
              ? 'bg-yellow-50 border-yellow-400'
              : 'bg-white/70 border-gray-400 hover:border-primary-400'
          }
        `}
      >
        {placedLabel ? (
          <span className="text-sm font-medium text-green-800 px-2 text-center">
            {placedLabel.text}
          </span>
        ) : (
          <span className="text-xs text-gray-400">?</span>
        )}
      </div>

      {/* Hint tooltip */}
      {showHint && hintText && !placedLabel && (
        <div className="absolute left-1/2 -translate-x-1/2 top-full mt-1 z-10">
          <div className="bg-yellow-100 border border-yellow-300 rounded px-2 py-1 text-xs text-yellow-800 whitespace-nowrap max-w-[200px] truncate">
            {hintText}
          </div>
        </div>
      )}

      {/* Correct placement indicator */}
      {placedLabel?.isCorrect && (
        <div className="absolute -top-1 -right-1">
          <div className="w-5 h-5 bg-green-500 rounded-full flex items-center justify-center">
            <svg className="w-3 h-3 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
            </svg>
          </div>
        </div>
      )}
    </div>
  );
}
