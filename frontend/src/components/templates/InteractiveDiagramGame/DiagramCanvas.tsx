'use client';

import { useMemo, useState, useCallback } from 'react';
import { Zone, PlacedLabel, Label, Hint, ZoneGroup, MediaAsset } from './types';
import DropZone from './DropZone';

/**
 * Convert a closed polygon to a smooth SVG path using Catmull-Rom → cubic Bezier.
 * Points are in 0-100 percentage space. tension=0.5 gives a smooth curve through all points.
 */
function smoothPolygonPath(points: [number, number][], tension = 0.5): string {
  if (!points || points.length < 3) return '';

  const n = points.length;
  // Build a closed Catmull-Rom spline: for each segment i→i+1,
  // use points (i-1, i, i+1, i+2) with wrapping
  const getP = (i: number) => points[((i % n) + n) % n];

  let d = `M ${getP(0)[0]} ${getP(0)[1]}`;

  for (let i = 0; i < n; i++) {
    const p0 = getP(i - 1);
    const p1 = getP(i);
    const p2 = getP(i + 1);
    const p3 = getP(i + 2);

    // Catmull-Rom to cubic Bezier control points
    const cp1x = p1[0] + (p2[0] - p0[0]) / (6 / tension);
    const cp1y = p1[1] + (p2[1] - p0[1]) / (6 / tension);
    const cp2x = p2[0] - (p3[0] - p1[0]) / (6 / tension);
    const cp2y = p2[1] - (p3[1] - p1[1]) / (6 / tension);

    d += ` C ${cp1x.toFixed(2)} ${cp1y.toFixed(2)}, ${cp2x.toFixed(2)} ${cp2y.toFixed(2)}, ${p2[0].toFixed(2)} ${p2[1].toFixed(2)}`;
  }

  return d;
}

/**
 * PolygonOverlay renders all polygon zone outlines in a single full-canvas SVG.
 * Using one SVG with viewBox="0 0 100 100" (percentage space) avoids
 * per-zone bounding box distortion from preserveAspectRatio="none".
 */
function PolygonOverlay({
  zones,
  placedZoneIds,
  activeDropZoneId,
  hierarchyColors = ['#60a5fa', '#a78bfa', '#2dd4bf'],
}: {
  zones: Zone[];
  placedZoneIds: Set<string>;
  activeDropZoneId?: string | null;
  hierarchyColors?: string[];
}) {
  const polygonZones = useMemo(
    () => zones.filter(z => z.shape === 'polygon' && z.points && z.points.length >= 3),
    [zones]
  );

  if (polygonZones.length === 0) return null;

  return (
    <svg
      className="absolute inset-0 w-full h-full pointer-events-none"
      viewBox="0 0 100 100"
      preserveAspectRatio="none"
      aria-hidden="true"
    >
      {polygonZones.map((zone) => {
        // Hide correctly-placed zones — only the floating label remains
        if (placedZoneIds.has(zone.id)) return null;

        const isOver = activeDropZoneId === zone.id;
        const level = zone.hierarchyLevel ?? 1;
        const strokeColor = isOver
          ? '#6366f1'
          : hierarchyColors[level - 1] ?? '#9ca3af';

        const pathD = smoothPolygonPath(zone.points as [number, number][]);

        return (
          <path
            key={zone.id}
            d={pathD}
            fill={isOver ? 'rgba(99, 102, 241, 0.15)' : 'rgba(96, 165, 250, 0.06)'}
            stroke={strokeColor}
            strokeWidth={isOver ? 2.5 : 1.5}
            strokeDasharray={isOver ? '6 2' : '8 4'}
            strokeLinecap="round"
            strokeLinejoin="round"
            vectorEffect="non-scaling-stroke"
            className="transition-all duration-200"
          />
        );
      })}
    </svg>
  );
}

/**
 * MediaAssetsLayer - Renders media assets (images, gifs, animations) on the diagram
 *
 * Supports:
 * - Background assets (full canvas)
 * - Overlay assets (positioned on top)
 * - Zone-attached assets (positioned relative to zones)
 * - CSS animations
 */
function MediaAssetsLayer({
  assets,
  zones,
}: {
  assets: MediaAsset[];
  zones: Zone[];
}) {
  // Sort assets by layer (lower layers render first)
  const sortedAssets = [...assets].sort((a, b) => (a.layer || 0) - (b.layer || 0));

  return (
    <>
      {sortedAssets.map((asset) => {
        const zone = asset.zoneId ? zones.find((z) => z.id === asset.zoneId) : null;

        // Base style for positioning
        const style: React.CSSProperties = {
          position: 'absolute',
          zIndex: 10 + (asset.layer || 0),
          pointerEvents: 'none', // Don't interfere with zone interactions
        };

        // Position based on placement type
        if (asset.placement === 'background') {
          Object.assign(style, {
            top: 0,
            left: 0,
            width: '100%',
            height: '100%',
            zIndex: -1, // Behind everything
            objectFit: 'cover',
          });
        } else if (asset.placement === 'zone' && zone) {
          // Position relative to zone center
          Object.assign(style, {
            left: `${zone.x || 50}%`,
            top: `${zone.y || 50}%`,
            transform: 'translate(-50%, -50%)',
            maxWidth: `${(zone.radius || 10) * 4}%`,
            maxHeight: `${(zone.radius || 10) * 4}%`,
          });
        } else if (asset.placement === 'overlay') {
          // Overlay covers entire canvas
          Object.assign(style, {
            top: 0,
            left: 0,
            width: '100%',
            height: '100%',
            objectFit: 'contain',
          });
        } else if (asset.placement === 'decoration') {
          // Decorations positioned at zone or center
          if (zone) {
            Object.assign(style, {
              left: `${zone.x || 50}%`,
              top: `${zone.y || 50}%`,
              transform: 'translate(-50%, -50%)',
            });
          } else {
            // Center if no zone specified
            Object.assign(style, {
              left: '50%',
              top: '50%',
              transform: 'translate(-50%, -50%)',
            });
          }
        }

        // Render based on asset type
        switch (asset.type) {
          case 'image':
          case 'gif':
            return asset.url ? (
              <img
                key={asset.id}
                src={asset.url}
                alt=""
                style={style}
                className="transition-opacity duration-300"
                aria-hidden="true"
              />
            ) : null;

          case 'video':
            return asset.url ? (
              <video
                key={asset.id}
                src={asset.url}
                style={style}
                autoPlay
                loop
                muted
                playsInline
                aria-hidden="true"
              />
            ) : null;

          case 'sprite':
            return asset.url ? (
              <div
                key={asset.id}
                style={{
                  ...style,
                  backgroundImage: `url(${asset.url})`,
                  backgroundSize: 'contain',
                  backgroundRepeat: 'no-repeat',
                }}
                aria-hidden="true"
              />
            ) : null;

          case 'css_animation':
            return (
              <div
                key={asset.id}
                style={style}
                className={`animate-${asset.id}`}
                aria-hidden="true"
              />
            );

          default:
            return null;
        }
      })}
    </>
  );
}

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
  zoneGroups?: ZoneGroup[];  // HAD v3: For collision detection
  mediaAssets?: MediaAsset[];  // Phase 3: Media assets for rendering
  // Accessibility props
  title?: string;  // Game title for ARIA context
  activeDragId?: string | null;  // Currently selected label for keyboard navigation
  onKeyboardDrop?: (labelId: string, zoneId: string) => void;  // Callback for keyboard drops
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
  zoneGroups = [],
  mediaAssets = [],
  title = 'Interactive Diagram',
  activeDragId,
  onKeyboardDrop,
}: DiagramCanvasProps) {
  // Hover tracking for zone highlighting
  const [hoveredZoneId, setHoveredZoneId] = useState<string | null>(null);
  const handleZoneHover = useCallback((zoneId: string | null) => {
    setHoveredZoneId(zoneId);
  }, []);

  // Create a map for quick lookup of placed labels
  // When label has canonicalName (description mode), show the zone name after correct placement
  const placedLabelMap = new Map(
    placedLabels.map((pl) => {
      const label = labels.find((l) => l.id === pl.labelId);
      const displayText = pl.isCorrect && label?.canonicalName
        ? label.canonicalName
        : label?.text || '';
      return [pl.zoneId, { ...pl, text: displayText }];
    })
  );

  // Create a map for hints
  // First priority: blueprint.hints array ({zoneId, hintText})
  // Second priority: zone.hint property (from zone detection)
  const hintMap = new Map(hints?.map((h) => [h.zoneId, h.hintText]) || []);
  // Add zone-level hints as fallback (from gemini_zone_detector)
  zones.forEach((zone) => {
    if (zone.hint && !hintMap.has(zone.id)) {
      hintMap.set(zone.id, zone.hint);
    }
  });

  // Calculate completion status for screen reader announcement
  const filledZones = placedLabels.length;
  const totalZones = zones.length;
  const completionStatus = `${filledZones} of ${totalZones} zones filled`;

  // Determine if we have polygon zones — if so, the image drives container sizing
  // to ensure zone percentage coordinates align with the image
  const hasPolygonZones = zones.some(z => z.shape === 'polygon' && z.points && z.points.length >= 3);

  return (
    <div
      role="application"
      aria-label={`Interactive diagram labeling game: ${title}`}
      aria-describedby="diagram-instructions"
      className="relative bg-gray-100 dark:bg-gray-800 rounded-lg overflow-hidden mx-auto"
      style={{
        width: '100%',
        maxWidth: `${width}px`,
        // When polygon zones are present, let the image drive the container height
        // so zone percentage coordinates (relative to image) align correctly.
        // Without polygon zones, use the blueprint aspect ratio as before.
        ...(!hasPolygonZones ? { aspectRatio: `${width} / ${height}` } : {}),
      }}
    >
      {/* Screen reader instructions */}
      <div id="diagram-instructions" className="sr-only">
        Drag labels from the tray to the correct zones on the diagram, or use Tab to navigate
        between zones and Enter to place the selected label. {completionStatus}.
      </div>
      {/* Diagram image or placeholder */}
      {assetUrl ? (
        <img
          src={assetUrl}
          alt={`Educational diagram: ${title}. Contains ${totalZones} labeled zones to identify.`}
          className={hasPolygonZones ? "w-full h-auto block" : "w-full h-full object-contain"}
        />
      ) : (
        <div className="w-full h-full flex flex-col items-center justify-center p-8 bg-gradient-to-br from-gray-100 to-gray-200 dark:from-gray-800 dark:to-gray-900">
          <svg
            className="w-24 h-24 text-gray-400 dark:text-gray-500 mb-4"
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

      {/* Media assets layer (Phase 3) */}
      {mediaAssets && mediaAssets.length > 0 && (
        <MediaAssetsLayer assets={mediaAssets} zones={zones} />
      )}

      {/* Full-canvas polygon overlay — renders smooth outlines for all polygon zones */}
      {hasPolygonZones && (
        <PolygonOverlay
          zones={zones}
          placedZoneIds={new Set(placedLabels.map(pl => pl.zoneId))}
          activeDropZoneId={hoveredZoneId}
        />
      )}

      {/* Drop zones overlay (interaction hit areas + labels) */}
      {zones.map((zone, index) => (
        <DropZone
          key={zone.id}
          zone={zone}
          placedLabel={placedLabelMap.get(zone.id)}
          showHint={showHints}
          hintText={hintMap.get(zone.id)}
          allZones={zones}  // HAD v3: For collision detection
          zoneGroups={zoneGroups}  // HAD v3: For layered relationship detection
          hierarchyLevel={zone.hierarchyLevel}  // HAD v3: Visual differentiation
          useCanvasOverlay={hasPolygonZones}  // Skip per-zone SVG when canvas overlay handles it
          onHover={handleZoneHover}
          // Accessibility props
          activeDragId={activeDragId}
          onKeyboardDrop={onKeyboardDrop}
          zoneIndex={index + 1}
          totalZones={totalZones}
        />
      ))}
    </div>
  );
}
