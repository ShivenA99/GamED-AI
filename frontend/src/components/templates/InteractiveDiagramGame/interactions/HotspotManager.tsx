'use client';

import { useState, useCallback, useEffect } from 'react';
import { Zone, IdentificationPrompt, IdentificationProgress, AnimationSpec } from '../types';
import { useAnimation, DEFAULT_ANIMATIONS } from '../animations/useAnimation';

interface HotspotManagerProps {
  zones: Zone[];
  prompts: IdentificationPrompt[];
  selectionMode: 'sequential' | 'any_order';
  onZoneClick: (zoneId: string, isCorrect: boolean) => void;
  onAllComplete: () => void;
  progress: IdentificationProgress | null;
  assetUrl?: string;
  width?: number;
  height?: number;
  animations?: {
    correctPlacement?: AnimationSpec;
    incorrectPlacement?: AnimationSpec;
  };
  feedbackMessages?: {
    correct?: string;
    incorrect?: string;
  };
  feedbackDisplayMs?: number;
}

interface HotspotZoneProps {
  zone: Zone;
  isTarget: boolean;
  isCompleted: boolean;
  isHighlighted: boolean;
  onClick: () => void;
  animationRef: React.RefCallback<HTMLDivElement>;
}

function HotspotZone({
  zone,
  isTarget,
  isCompleted,
  isHighlighted,
  onClick,
  animationRef,
}: HotspotZoneProps) {
  const size = (zone.radius ?? 5) * 2;

  return (
    <div
      ref={animationRef}
      onClick={onClick}
      className={`
        absolute transform -translate-x-1/2 -translate-y-1/2
        cursor-pointer transition-all duration-200
        ${isCompleted ? 'opacity-50 pointer-events-none' : ''}
      `}
      style={{
        left: `${zone.x}%`,
        top: `${zone.y}%`,
        width: `${size}%`,
        minWidth: '50px',
        minHeight: '50px',
      }}
    >
      <div
        className={`
          w-full h-full rounded-full border-3
          flex items-center justify-center
          transition-all duration-200
          ${
            isCompleted
              ? 'bg-green-100/50 border-green-500'
              : isTarget
              ? 'bg-yellow-100/70 border-yellow-400 animate-pulse'
              : isHighlighted
              ? 'bg-blue-100/50 border-blue-400'
              : 'bg-transparent border-transparent hover:bg-blue-50/30 hover:border-blue-300'
          }
        `}
      >
        {isCompleted && (
          <div className="w-6 h-6 bg-green-500 rounded-full flex items-center justify-center">
            <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
            </svg>
          </div>
        )}
      </div>

      {/* Zone label on hover (if not completed) */}
      {!isCompleted && (
        <div className="absolute left-1/2 -translate-x-1/2 top-full mt-1 z-10 opacity-0 hover:opacity-100 transition-opacity">
          <div className="bg-gray-800 text-white rounded px-2 py-1 text-xs whitespace-nowrap">
            {zone.label}
          </div>
        </div>
      )}
    </div>
  );
}

export default function HotspotManager({
  zones,
  prompts,
  selectionMode,
  onZoneClick,
  onAllComplete,
  progress: externalProgress,
  assetUrl,
  width = 800,
  height = 600,
  animations,
  feedbackMessages,
  feedbackDisplayMs = 1500,
}: HotspotManagerProps) {
  const { animate } = useAnimation();

  // Sort prompts by order for sequential mode
  const sortedPrompts = [...prompts].sort((a, b) => (a.order || 0) - (b.order || 0));

  // MF-3: Always use external progress prop — eliminate dual-state desync
  // If external progress isn't provided, use a default (but parent should always pass it)
  const progress = externalProgress || {
    currentPromptIndex: 0,
    completedZoneIds: [] as string[],
    incorrectAttempts: 0,
  };

  const [feedbackMessage, setFeedbackMessage] = useState<string | null>(null);
  const [zoneRefs, setZoneRefs] = useState<Map<string, HTMLDivElement>>(new Map());

  const currentPrompt = selectionMode === 'sequential' ? sortedPrompts[progress.currentPromptIndex] : null;

  // Get remaining prompts for any_order mode
  const remainingPrompts = sortedPrompts.filter(
    (p) => !progress.completedZoneIds.includes(p.zoneId)
  );

  const handleZoneClick = useCallback(
    (zoneId: string) => {
      let isCorrect = false;

      if (selectionMode === 'sequential') {
        // In sequential mode, must click the current target
        isCorrect = currentPrompt?.zoneId === zoneId;
      } else {
        // In any_order mode, any remaining correct zone is valid
        isCorrect = remainingPrompts.some((p) => p.zoneId === zoneId);
      }

      // Get the zone element for animation
      const zoneElement = zoneRefs.get(zoneId);

      if (isCorrect) {
        // Animate correct
        if (zoneElement) {
          animate(
            zoneElement,
            animations?.correctPlacement || DEFAULT_ANIMATIONS.correctPlacement
          );
        }

        // MF-3: Parent is sole source of truth — no internal state mutation
        setFeedbackMessage(feedbackMessages?.correct ?? 'Correct!');
        onZoneClick(zoneId, true);
      } else {
        // Animate incorrect
        if (zoneElement) {
          animate(
            zoneElement,
            animations?.incorrectPlacement || DEFAULT_ANIMATIONS.incorrectPlacement
          );
        }

        // MF-3: Parent is sole source of truth — no internal state mutation
        setFeedbackMessage(feedbackMessages?.incorrect ?? 'Try again!');
        onZoneClick(zoneId, false);
      }

      // Clear feedback after delay
      setTimeout(() => setFeedbackMessage(null), feedbackDisplayMs);
    },
    [
      selectionMode,
      currentPrompt,
      remainingPrompts,
      animate,
      animations,
      onZoneClick,
      zoneRefs,
      externalProgress,
    ]
  );

  // Check for completion
  useEffect(() => {
    if (progress.completedZoneIds.length === prompts.length && prompts.length > 0) {
      onAllComplete();
    }
  }, [progress.completedZoneIds.length, prompts.length, onAllComplete]);

  // Create ref callback for zones
  const createZoneRef = useCallback(
    (zoneId: string) => (el: HTMLDivElement | null) => {
      if (el) {
        setZoneRefs((prev) => new Map(prev).set(zoneId, el));
      }
    },
    []
  );

  const isZoneTarget = (zoneId: string) => {
    if (selectionMode === 'sequential') {
      return currentPrompt?.zoneId === zoneId;
    }
    return remainingPrompts.some((p) => p.zoneId === zoneId);
  };

  const isZoneCompleted = (zoneId: string) => {
    return progress.completedZoneIds.includes(zoneId);
  };

  // Get current prompt text
  // Fix 6.4: Don't leak zone labels in any_order mode
  const currentPromptText =
    selectionMode === 'sequential'
      ? currentPrompt?.prompt
      : remainingPrompts.length > 0
      ? `Click on the next structure (${progress.completedZoneIds.length} of ${prompts.length} identified)`
      : 'All identified!';

  return (
    <div
      className="relative mx-auto my-6"
      style={{
        width: '100%',
        maxWidth: `${width}px`,
        aspectRatio: `${width} / ${height}`,
      }}
    >
      {/* Background image */}
      {assetUrl && (
        <img
          src={assetUrl}
          alt="Diagram"
          className="absolute inset-0 w-full h-full object-contain pointer-events-none"
        />
      )}

      {/* Prompt display */}
      <div className="absolute top-4 left-1/2 -translate-x-1/2 z-20">
        <div className="bg-blue-600 text-white rounded-lg px-4 py-2 shadow-lg">
          <p className="text-sm font-medium">{currentPromptText}</p>
        </div>
      </div>

      {/* Progress indicator */}
      <div className="absolute top-4 right-4 z-20">
        <div className="bg-white rounded-lg px-3 py-2 shadow-md">
          <p className="text-sm text-gray-700">
            {progress.completedZoneIds.length} / {prompts.length}
          </p>
        </div>
      </div>

      {/* Hotspot zones */}
      {zones.map((zone) => (
        <HotspotZone
          key={zone.id}
          zone={zone}
          isTarget={isZoneTarget(zone.id)}
          isCompleted={isZoneCompleted(zone.id)}
          isHighlighted={false}
          onClick={() => handleZoneClick(zone.id)}
          animationRef={createZoneRef(zone.id)}
        />
      ))}

      {/* Feedback message */}
      {feedbackMessage && (
        <div className="absolute bottom-4 left-1/2 -translate-x-1/2 z-20 animate-fade-in">
          <div
            className={`rounded-lg px-4 py-2 shadow-lg ${
              feedbackMessage === 'Correct!'
                ? 'bg-green-500 text-white'
                : 'bg-red-500 text-white'
            }`}
          >
            <p className="text-sm font-medium">{feedbackMessage}</p>
          </div>
        </div>
      )}
    </div>
  );
}
