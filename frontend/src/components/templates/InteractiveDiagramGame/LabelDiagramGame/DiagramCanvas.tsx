'use client';

import { Zone, PlacedLabel, Label, Hint } from './types';
import DropZone from './DropZone';

interface DiagramCanvasProps {
  assetUrl?: string;
  assetPrompt: string;
  zones: Zone[];
  placedLabels: PlacedLabel[];
  labels: Label[];
  hints?: Hint[];
  showHints: boolean;
  width?: number;
  height?: number;
}

export default function DiagramCanvas({
  assetUrl,
  assetPrompt,
  zones,
  placedLabels,
  labels,
  hints,
  showHints,
  width = 800,
  height = 600,
}: DiagramCanvasProps) {
  // Create a map for quick lookup of placed labels
  const placedLabelMap = new Map(
    placedLabels.map((pl) => {
      const label = labels.find((l) => l.id === pl.labelId);
      return [pl.zoneId, { ...pl, text: label?.text || '' }];
    })
  );

  // Create a map for hints
  const hintMap = new Map(hints?.map((h) => [h.zoneId, h.hintText]) || []);

  return (
    <div
      className="relative bg-gray-100 rounded-lg overflow-hidden mx-auto"
      style={{
        width: '100%',
        maxWidth: `${width}px`,
        aspectRatio: `${width} / ${height}`,
      }}
    >
      {/* Diagram image or placeholder */}
      {assetUrl ? (
        <img
          src={assetUrl}
          alt="Diagram to label"
          className="w-full h-full object-contain"
        />
      ) : (
        <div className="w-full h-full flex flex-col items-center justify-center p-8 bg-gradient-to-br from-gray-100 to-gray-200">
          <svg
            className="w-24 h-24 text-gray-400 mb-4"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={1.5}
              d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
            />
          </svg>
          <p className="text-gray-500 text-center text-sm max-w-md">
            {assetPrompt}
          </p>
          <p className="text-gray-400 text-xs mt-2">
            (Diagram visualization placeholder)
          </p>
        </div>
      )}

      {/* Drop zones overlay */}
      {zones.map((zone) => (
        <DropZone
          key={zone.id}
          zone={zone}
          placedLabel={placedLabelMap.get(zone.id)}
          showHint={showHints}
          hintText={hintMap.get(zone.id)}
        />
      ))}
    </div>
  );
}
