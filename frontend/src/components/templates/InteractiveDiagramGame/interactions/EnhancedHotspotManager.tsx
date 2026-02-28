'use client';

import React, { useState, useCallback, useMemo, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import type { Zone, IdentificationPrompt, ClickToIdentifyConfig, MechanicAction, ActionResult } from '../types';
import { findZoneAtPoint } from '../hooks/useZoneCollision';

export interface EnhancedHotspotManagerProps {
  zones: Zone[];
  prompts: IdentificationPrompt[];
  config?: ClickToIdentifyConfig;
  assetUrl?: string;
  width?: number;
  height?: number;
  /** Source-of-truth progress from store. Component derives all visual state from this. */
  progress?: { currentPromptIndex: number; completedZoneIds: string[]; incorrectAttempts: number } | null;
  /** Unified action dispatch — the only output channel. */
  onAction: (action: MechanicAction) => ActionResult | null;
}

type ZoneVisualState = 'default' | 'hover' | 'correct' | 'incorrect' | 'disabled';

// ─── Prompt Banner ──────────────────────────────────────────────────
function PromptBanner({
  prompt,
  currentIndex,
  total,
  style,
}: {
  prompt: string;
  currentIndex: number;
  total: number;
  style: 'naming' | 'functional';
}) {
  return (
    <motion.div
      key={prompt}
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      className="w-full bg-gradient-to-r from-indigo-600 to-blue-600 text-white rounded-xl px-6 py-4 shadow-lg mb-4"
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3 flex-1">
          <div className="w-8 h-8 rounded-full bg-white/20 flex items-center justify-center text-sm font-bold flex-shrink-0">
            {currentIndex + 1}
          </div>
          <p className="text-base font-medium leading-snug">{prompt}</p>
        </div>
        <div className="flex-shrink-0 ml-4">
          <span className="text-sm text-white/70 bg-white/10 px-3 py-1 rounded-full">
            {currentIndex + 1} of {total}
          </span>
        </div>
      </div>

      {/* Progress bar */}
      <div className="mt-3 w-full h-1.5 bg-white/20 rounded-full overflow-hidden">
        <motion.div
          className="h-full bg-white/70 rounded-full"
          initial={{ width: 0 }}
          animate={{ width: `${((currentIndex) / total) * 100}%` }}
          transition={{ type: 'spring', stiffness: 80 }}
        />
      </div>
    </motion.div>
  );
}

// ─── Magnification Lens ─────────────────────────────────────────────
function MagnificationLens({
  imageUrl,
  cursorX,
  cursorY,
  containerRect,
  factor,
  diameter,
  show,
}: {
  imageUrl: string;
  cursorX: number;
  cursorY: number;
  containerRect: DOMRect | null;
  factor: number;
  diameter: number;
  show: boolean;
}) {
  if (!show || !containerRect || !imageUrl) return null;

  const relX = cursorX - containerRect.left;
  const relY = cursorY - containerRect.top;

  // Background position for magnified view
  const bgPosX = -(relX * factor - diameter / 2);
  const bgPosY = -(relY * factor - diameter / 2);
  const bgWidth = containerRect.width * factor;
  const bgHeight = containerRect.height * factor;

  return (
    <div
      className="fixed pointer-events-none z-50 rounded-full border-4 border-white shadow-2xl overflow-hidden"
      style={{
        left: cursorX - diameter / 2,
        top: cursorY - diameter / 2,
        width: diameter,
        height: diameter,
        backgroundImage: `url(${imageUrl})`,
        backgroundPosition: `${bgPosX}px ${bgPosY}px`,
        backgroundSize: `${bgWidth}px ${bgHeight}px`,
        backgroundRepeat: 'no-repeat',
      }}
    >
      {/* Crosshair */}
      <div className="absolute inset-0 flex items-center justify-center">
        <div className="w-4 h-px bg-red-500/50" />
        <div className="absolute w-px h-4 bg-red-500/50" />
      </div>
    </div>
  );
}

// ─── SVG Zone Shape Helper ──────────────────────────────────────────
function ZoneShape({
  zone,
  visualState,
  highlightStyle,
}: {
  zone: Zone;
  visualState: ZoneVisualState;
  highlightStyle: string;
}) {
  const getColors = () => {
    switch (visualState) {
      case 'correct':
        return { fill: 'rgba(34,197,94,0.3)', stroke: '#22c55e', strokeWidth: 2 };
      case 'incorrect':
        return { fill: 'rgba(239,68,68,0.3)', stroke: '#ef4444', strokeWidth: 2 };
      case 'hover':
        return { fill: 'rgba(99,102,241,0.2)', stroke: '#6366f1', strokeWidth: 2 };
      case 'disabled':
        return { fill: 'rgba(156,163,175,0.2)', stroke: '#9ca3af', strokeWidth: 1 };
      default: {
        // Nearly invisible by default — no process-of-elimination
        const opacity = highlightStyle === 'invisible' ? 0 : highlightStyle === 'subtle' ? 0.05 : 0.15;
        return { fill: `rgba(148,163,184,${opacity})`, stroke: `rgba(148,163,184,${opacity * 2})`, strokeWidth: 1 };
      }
    }
  };

  const { fill, stroke, strokeWidth } = getColors();

  // Polygon zone
  if (zone.shape === 'polygon' && zone.points && zone.points.length >= 3) {
    const pathData = zone.points.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p[0]} ${p[1]}`).join(' ') + ' Z';
    return (
      <path
        d={pathData}
        fill={fill}
        stroke={stroke}
        strokeWidth={strokeWidth}
        className="transition-all duration-200"
        style={{ cursor: 'pointer' }}
      />
    );
  }

  // Circle zone (fallback)
  const cx = zone.center?.x ?? zone.x ?? 50;
  const cy = zone.center?.y ?? zone.y ?? 50;
  const r = zone.radius ?? 4;

  return (
    <circle
      cx={cx}
      cy={cy}
      r={r}
      fill={fill}
      stroke={stroke}
      strokeWidth={strokeWidth}
      className="transition-all duration-200"
      style={{ cursor: 'pointer' }}
    />
  );
}

// ─── Correct Indicator (HTML overlay on top of SVG) ─────────────────
function CorrectIndicator({ zone }: { zone: Zone }) {
  const cx = zone.center?.x ?? zone.x ?? 50;
  const cy = zone.center?.y ?? zone.y ?? 50;

  return (
    <div
      className="absolute transform -translate-x-1/2 -translate-y-1/2 pointer-events-none"
      style={{ left: `${cx}%`, top: `${cy}%` }}
    >
      <motion.div
        initial={{ scale: 0 }}
        animate={{ scale: 1 }}
        transition={{ type: 'spring', stiffness: 300 }}
        className="flex items-center gap-1.5"
      >
        <div className="w-6 h-6 bg-green-500 rounded-full flex items-center justify-center shadow-md">
          <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
          </svg>
        </div>
        <span className="bg-green-100 dark:bg-green-900/50 text-green-800 dark:text-green-300 text-xs font-medium px-2 py-0.5 rounded shadow-sm whitespace-nowrap">
          {zone.label}
        </span>
      </motion.div>
    </div>
  );
}

// ─── Main Component ─────────────────────────────────────────────────
export function EnhancedHotspotManager({
  zones,
  prompts,
  config,
  assetUrl,
  width = 800,
  height = 600,
  progress,
  onAction,
}: EnhancedHotspotManagerProps) {
  const {
    promptStyle = 'naming',
    selectionMode = 'sequential',
    highlightStyle = 'subtle',
    magnificationEnabled = false,
    magnificationFactor = 2.5,
    showZoneCount = true,
    instructions,
  } = config || {};

  const containerRef = useRef<HTMLDivElement>(null);

  // Derive persistent state from progress prop (source of truth)
  const completedZoneIds = useMemo(
    () => new Set(progress?.completedZoneIds || []),
    [progress?.completedZoneIds]
  );
  const currentPromptIndex = progress?.currentPromptIndex ?? 0;

  // Transient visual state only — not game state
  const [hoveredZoneId, setHoveredZoneId] = useState<string | null>(null);
  const [incorrectZoneId, setIncorrectZoneId] = useState<string | null>(null);
  const [cursorPos, setCursorPos] = useState({ x: 0, y: 0 });
  const [containerRect, setContainerRect] = useState<DOMRect | null>(null);
  const [showMagnifier, setShowMagnifier] = useState(false);

  // Sort prompts by order
  const sortedPrompts = useMemo(
    () => [...prompts].sort((a, b) => (a.order ?? 0) - (b.order ?? 0)),
    [prompts]
  );

  const currentPrompt = sortedPrompts[currentPromptIndex];
  const isComplete = completedZoneIds.size >= sortedPrompts.length;

  // Handle zone click — emit action, use ActionResult for transient visual feedback
  const handleZoneClick = useCallback((zoneId: string) => {
    if (completedZoneIds.has(zoneId) || isComplete) return;

    // Emit unified action — store handles correctness, scoring, and completion
    const result = onAction({ type: 'identify', mechanic: 'click_to_identify', zoneId });

    // Transient visual feedback from ActionResult
    if (result && !result.isCorrect) {
      setIncorrectZoneId(zoneId);
      setTimeout(() => setIncorrectZoneId(null), 600);
    }
  }, [completedZoneIds, isComplete, onAction]);

  // Container click handler — converts pixel coords to % and finds zone
  const handleContainerClick = useCallback((e: React.MouseEvent) => {
    const container = containerRef.current;
    if (!container) return;
    const img = container.querySelector('img');
    const imgRect = img?.getBoundingClientRect() || container.getBoundingClientRect();
    const pctX = ((e.clientX - imgRect.left) / imgRect.width) * 100;
    const pctY = ((e.clientY - imgRect.top) / imgRect.height) * 100;
    const zone = findZoneAtPoint(pctX, pctY, zones);
    if (zone) handleZoneClick(zone.id);
  }, [zones, handleZoneClick]);

  // Mouse tracking for hover state and magnifier
  const handleMouseMove = useCallback((e: React.MouseEvent) => {
    if (magnificationEnabled) {
      setCursorPos({ x: e.clientX, y: e.clientY });
      if (containerRef.current) {
        setContainerRect(containerRef.current.getBoundingClientRect());
      }
    }
    // Update hover
    const container = containerRef.current;
    if (!container) return;
    const img = container.querySelector('img');
    const imgRect = img?.getBoundingClientRect() || container.getBoundingClientRect();
    const pctX = ((e.clientX - imgRect.left) / imgRect.width) * 100;
    const pctY = ((e.clientY - imgRect.top) / imgRect.height) * 100;
    const zone = findZoneAtPoint(pctX, pctY, zones);
    setHoveredZoneId(zone?.id ?? null);
  }, [zones, magnificationEnabled]);

  // Get visual state for each zone
  const getZoneState = useCallback((zoneId: string): ZoneVisualState => {
    if (completedZoneIds.has(zoneId)) return 'correct';
    if (incorrectZoneId === zoneId) return 'incorrect';
    if (hoveredZoneId === zoneId) return 'hover';
    return 'default';
  }, [completedZoneIds, incorrectZoneId, hoveredZoneId]);

  return (
    <div className="w-full max-w-4xl mx-auto">
      {/* Prompt banner */}
      {currentPrompt && !isComplete && (
        <PromptBanner
          prompt={currentPrompt.prompt}
          currentIndex={currentPromptIndex}
          total={sortedPrompts.length}
          style={promptStyle}
        />
      )}

      {/* Completion message */}
      {isComplete && (
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          className="mb-4 p-4 bg-green-50 dark:bg-green-900/20 border-2 border-green-300 dark:border-green-700 rounded-xl text-center"
        >
          <p className="text-lg font-bold text-green-800 dark:text-green-200">All structures identified!</p>
        </motion.div>
      )}

      {/* Diagram with interactive zones */}
      <div
        ref={containerRef}
        className="relative rounded-xl overflow-hidden bg-gray-100 dark:bg-gray-800 mx-auto cursor-crosshair"
        style={{ maxWidth: `${width}px`, aspectRatio: `${width} / ${height}` }}
        onClick={handleContainerClick}
        onMouseMove={handleMouseMove}
        onMouseEnter={() => magnificationEnabled && setShowMagnifier(true)}
        onMouseLeave={() => { setShowMagnifier(false); setHoveredZoneId(null); }}
      >
        {/* Diagram image */}
        {assetUrl && (
          <img
            src={assetUrl}
            alt="Educational diagram"
            className="w-full h-full object-contain pointer-events-none"
            draggable={false}
          />
        )}

        {/* SVG overlay for zone shapes */}
        <svg
          className="absolute inset-0 w-full h-full pointer-events-none"
          viewBox="0 0 100 100"
          preserveAspectRatio="none"
        >
          {zones.map((zone) => (
            <ZoneShape
              key={zone.id}
              zone={zone}
              visualState={getZoneState(zone.id)}
              highlightStyle={highlightStyle}
            />
          ))}
        </svg>

        {/* Correct indicators (HTML layer on top) */}
        {zones.filter(z => completedZoneIds.has(z.id)).map(zone => (
          <CorrectIndicator key={`correct-${zone.id}`} zone={zone} />
        ))}
      </div>

      {/* Magnification lens */}
      {magnificationEnabled && assetUrl && (
        <MagnificationLens
          imageUrl={assetUrl}
          cursorX={cursorPos.x}
          cursorY={cursorPos.y}
          containerRect={containerRect}
          factor={magnificationFactor || 2.5}
          diameter={90}
          show={showMagnifier}
        />
      )}
    </div>
  );
}

export default EnhancedHotspotManager;
