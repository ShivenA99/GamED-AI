'use client';

import { useCallback, useRef, useMemo, useEffect } from 'react';
import { AnimationSpec, AnimationType, EasingType, MotionPath, MotionKeyframe, MotionTrigger } from '../types';

interface AnimationOptions {
  onComplete?: () => void;
  onStart?: () => void;
}

// CSS keyframe definitions for each animation type
const ANIMATION_KEYFRAMES: Record<AnimationType, string> = {
  pulse: `
    @keyframes pulse {
      0%, 100% { transform: scale(1); opacity: 1; }
      50% { transform: scale(1.1); opacity: 0.8; }
    }
  `,
  glow: `
    @keyframes glow {
      0%, 100% { box-shadow: 0 0 5px var(--glow-color, #3b82f6); }
      50% { box-shadow: 0 0 20px var(--glow-color, #3b82f6), 0 0 30px var(--glow-color, #3b82f6); }
    }
  `,
  scale: `
    @keyframes scale {
      0% { transform: scale(1); }
      50% { transform: scale(1.15); }
      100% { transform: scale(1); }
    }
  `,
  shake: `
    @keyframes shake {
      0%, 100% { transform: translateX(0); }
      10%, 30%, 50%, 70%, 90% { transform: translateX(-5px); }
      20%, 40%, 60%, 80% { transform: translateX(5px); }
    }
  `,
  fade: `
    @keyframes fade {
      0% { opacity: 0; }
      100% { opacity: 1; }
    }
  `,
  bounce: `
    @keyframes bounce {
      0%, 20%, 50%, 80%, 100% { transform: translateY(0); }
      40% { transform: translateY(-15px); }
      60% { transform: translateY(-8px); }
    }
  `,
  confetti: `
    @keyframes confetti {
      0% { opacity: 1; transform: translateY(0) rotate(0deg); }
      100% { opacity: 0; transform: translateY(-50px) rotate(720deg); }
    }
  `,
  path_draw: `
    @keyframes path_draw {
      0% { stroke-dashoffset: 1000; }
      100% { stroke-dashoffset: 0; }
    }
  `,
};

// Map easing types to CSS timing functions
const EASING_MAP: Record<EasingType, string> = {
  linear: 'linear',
  'ease-out': 'ease-out',
  'ease-in-out': 'ease-in-out',
  bounce: 'cubic-bezier(0.68, -0.55, 0.265, 1.55)',
  elastic: 'cubic-bezier(0.68, -0.6, 0.32, 1.6)',
};

// Reference counting for animation keyframe styles
const keyframeRefCounts = new Map<AnimationType, number>();

// Inject keyframes into document with reference counting for cleanup
const injectKeyframes = (type: AnimationType): void => {
  if (typeof document === 'undefined') return;

  const styleId = `animation-keyframes-${type}`;
  const currentCount = keyframeRefCounts.get(type) || 0;

  if (!document.getElementById(styleId)) {
    const style = document.createElement('style');
    style.id = styleId;
    style.textContent = ANIMATION_KEYFRAMES[type];
    document.head.appendChild(style);
  }

  keyframeRefCounts.set(type, currentCount + 1);
};

// Remove keyframes when no longer needed
const removeKeyframes = (type: AnimationType): void => {
  if (typeof document === 'undefined') return;

  const currentCount = keyframeRefCounts.get(type) || 0;
  if (currentCount <= 1) {
    const styleId = `animation-keyframes-${type}`;
    const style = document.getElementById(styleId);
    if (style) {
      style.remove();
    }
    keyframeRefCounts.delete(type);
  } else {
    keyframeRefCounts.set(type, currentCount - 1);
  }
};

/**
 * Hook for applying structured animations to elements
 */
export function useAnimation() {
  const animationTimeouts = useRef<Map<HTMLElement, number>>(new Map());
  // Track which animation types this hook instance has injected for cleanup
  const injectedTypesRef = useRef<Set<AnimationType>>(new Set());

  // Cleanup injected styles on unmount
  useEffect(() => {
    return () => {
      // Clean up all animation timeouts
      animationTimeouts.current.forEach((timeoutId) => {
        clearTimeout(timeoutId);
      });
      animationTimeouts.current.clear();

      // Clean up injected keyframes (decrement ref counts)
      injectedTypesRef.current.forEach((type) => {
        removeKeyframes(type);
      });
      injectedTypesRef.current.clear();
    };
  }, []);

  /**
   * Apply an animation to an element
   */
  const animate = useCallback(
    (
      element: HTMLElement | null,
      spec: AnimationSpec,
      options?: AnimationOptions
    ) => {
      if (!element) return;

      // Inject keyframes if needed and track for cleanup
      if (!injectedTypesRef.current.has(spec.type)) {
        injectKeyframes(spec.type);
        injectedTypesRef.current.add(spec.type);
      }

      // Clear any existing animation timeout
      const existingTimeout = animationTimeouts.current.get(element);
      if (existingTimeout) {
        clearTimeout(existingTimeout);
        element.style.animation = '';
      }

      // Apply animation CSS variables
      if (spec.color) {
        element.style.setProperty('--glow-color', spec.color);
        element.style.setProperty('--animation-color', spec.color);
      }

      // Calculate animation properties
      const duration = spec.duration_ms / 1000;
      const delay = (spec.delay_ms || 0) / 1000;
      const easing = EASING_MAP[spec.easing] || 'ease-out';
      const iterations = spec.type === 'confetti' ? 1 : spec.intensity || 1;

      // Start callback
      options?.onStart?.();

      // Apply animation
      element.style.animation = `${spec.type} ${duration}s ${easing} ${delay}s ${iterations}`;

      // Clean up after animation completes
      const totalDuration = (spec.duration_ms + (spec.delay_ms || 0)) * (iterations as number);
      const timeoutId = window.setTimeout(() => {
        element.style.animation = '';
        animationTimeouts.current.delete(element);
        options?.onComplete?.();
      }, totalDuration);

      animationTimeouts.current.set(element, timeoutId);
    },
    []
  );

  /**
   * Stop all animations on an element
   */
  const stopAnimation = useCallback((element: HTMLElement | null) => {
    if (!element) return;

    const timeoutId = animationTimeouts.current.get(element);
    if (timeoutId) {
      clearTimeout(timeoutId);
      animationTimeouts.current.delete(element);
    }
    element.style.animation = '';
  }, []);

  /**
   * Create CSS class string for inline animation styles
   */
  const getAnimationStyle = useCallback(
    (spec: AnimationSpec): React.CSSProperties => {
      injectKeyframes(spec.type);

      const duration = spec.duration_ms / 1000;
      const delay = (spec.delay_ms || 0) / 1000;
      const easing = EASING_MAP[spec.easing] || 'ease-out';

      return {
        animation: `${spec.type} ${duration}s ${easing} ${delay}s`,
        '--glow-color': spec.color,
        '--animation-color': spec.color,
      } as React.CSSProperties;
    },
    []
  );

  return {
    animate,
    stopAnimation,
    getAnimationStyle,
  };
}

/**
 * Default animation specs for common game events
 */
export const DEFAULT_ANIMATIONS: Record<string, AnimationSpec> = {
  correctPlacement: {
    type: 'pulse',
    duration_ms: 400,
    easing: 'ease-out',
    color: '#22c55e',
    intensity: 1,
  },
  incorrectPlacement: {
    type: 'shake',
    duration_ms: 300,
    easing: 'ease-out',
    color: '#ef4444',
    intensity: 1,
  },
  completion: {
    type: 'confetti',
    duration_ms: 2000,
    easing: 'ease-out',
    color: '#3b82f6',
    intensity: 1.5,
  },
  labelDrag: {
    type: 'scale',
    duration_ms: 150,
    easing: 'ease-out',
    intensity: 1,
  },
  zoneHover: {
    type: 'glow',
    duration_ms: 300,
    easing: 'ease-in-out',
    color: '#3b82f6',
    intensity: 1,
  },
  pathProgress: {
    type: 'path_draw',
    duration_ms: 500,
    easing: 'ease-out',
    color: '#22c55e',
    intensity: 1,
  },
};

// =============================================================================
// Motion Path Controller
// =============================================================================

interface MotionControllerOptions {
  onComplete?: () => void;
  onStart?: () => void;
}

/**
 * Hook for animating elements using motion paths.
 *
 * Uses the Web Animations API for smooth, performant keyframe-based animations.
 */
export function useMotionController(motionPaths: MotionPath[] = []) {
  const runningAnimations = useRef<Map<string, Animation>>(new Map());

  /**
   * Convert motion keyframes to Web Animations API format.
   */
  const convertKeyframes = useCallback((keyframes: MotionKeyframe[]): Keyframe[] => {
    const maxTime = keyframes[keyframes.length - 1]?.time_ms || 1;

    return keyframes.map((kf) => {
      const keyframe: Keyframe = {
        offset: kf.time_ms / maxTime,
      };

      // Build transform string
      const transforms: string[] = [];
      if (kf.x !== undefined || kf.y !== undefined) {
        const x = kf.x ?? 0;
        const y = kf.y ?? 0;
        transforms.push(`translate(${x}%, ${y}%)`);
      }
      if (kf.scale !== undefined) {
        transforms.push(`scale(${kf.scale})`);
      }
      if (kf.rotation !== undefined) {
        transforms.push(`rotate(${kf.rotation}deg)`);
      }
      if (kf.transform) {
        transforms.push(kf.transform);
      }

      if (transforms.length > 0) {
        keyframe.transform = transforms.join(' ');
      }

      if (kf.opacity !== undefined) {
        keyframe.opacity = kf.opacity;
      }

      if (kf.backgroundColor) {
        keyframe.backgroundColor = kf.backgroundColor;
      }

      return keyframe;
    });
  }, []);

  /**
   * Animate an element using a motion path.
   */
  const animateMotion = useCallback(
    (
      element: HTMLElement | null,
      motionPath: MotionPath,
      options?: MotionControllerOptions
    ) => {
      if (!element || !motionPath.keyframes.length) return;

      // Cancel any running animation on this element
      const existing = runningAnimations.current.get(motionPath.asset_id);
      if (existing) {
        existing.cancel();
      }

      // Convert keyframes
      const keyframes = convertKeyframes(motionPath.keyframes);
      const duration = motionPath.keyframes[motionPath.keyframes.length - 1]?.time_ms || 300;

      // Start callback
      options?.onStart?.();

      // Create and start animation
      const animation = element.animate(keyframes, {
        duration,
        easing: motionPath.easing || 'ease-in-out',
        fill: 'forwards',
        iterations: motionPath.loop ? Infinity : 1,
      });

      runningAnimations.current.set(motionPath.asset_id, animation);

      // Handle completion
      animation.onfinish = () => {
        runningAnimations.current.delete(motionPath.asset_id);
        options?.onComplete?.();
      };

      return animation;
    },
    [convertKeyframes]
  );

  /**
   * Play motion path by trigger type for a specific asset.
   */
  const playMotionPath = useCallback(
    (
      trigger: MotionTrigger,
      assetId: string,
      element: HTMLElement | null,
      options?: MotionControllerOptions
    ) => {
      const path = motionPaths.find(
        (p) => p.trigger === trigger && p.asset_id === assetId
      );

      if (path && element) {
        return animateMotion(element, path, options);
      }

      return null;
    },
    [motionPaths, animateMotion]
  );

  /**
   * Play all motion paths for a trigger type with stagger.
   */
  const playTriggerWithStagger = useCallback(
    (
      trigger: MotionTrigger,
      elements: Map<string, HTMLElement>,
      staggerMs: number = 100
    ) => {
      const paths = motionPaths.filter((p) => p.trigger === trigger);
      const animations: Animation[] = [];

      paths.forEach((path, index) => {
        const element = elements.get(path.asset_id);
        if (!element) return;

        // Apply stagger delay
        const delay = (path.stagger_delay_ms ?? staggerMs) * index;

        setTimeout(() => {
          const anim = animateMotion(element, path);
          if (anim) animations.push(anim);
        }, delay);
      });

      return animations;
    },
    [motionPaths, animateMotion]
  );

  /**
   * Stop all running animations.
   */
  const stopAllMotions = useCallback(() => {
    runningAnimations.current.forEach((animation) => {
      animation.cancel();
    });
    runningAnimations.current.clear();
  }, []);

  /**
   * Stop animation for a specific asset.
   */
  const stopMotion = useCallback((assetId: string) => {
    const animation = runningAnimations.current.get(assetId);
    if (animation) {
      animation.cancel();
      runningAnimations.current.delete(assetId);
    }
  }, []);

  return {
    animateMotion,
    playMotionPath,
    playTriggerWithStagger,
    stopAllMotions,
    stopMotion,
  };
}

/**
 * Create default motion paths for reveal animations.
 */
export function createRevealMotionPath(assetId: string): MotionPath {
  return {
    asset_id: assetId,
    keyframes: [
      { time_ms: 0, opacity: 0, scale: 0.9 },
      { time_ms: 300, opacity: 1, scale: 1.0 },
    ],
    easing: 'ease-out',
    trigger: 'on_reveal',
  };
}

/**
 * Create shake animation motion path for incorrect placements.
 */
export function createShakeMotionPath(assetId: string): MotionPath {
  return {
    asset_id: assetId,
    keyframes: [
      { time_ms: 0, x: 0 },
      { time_ms: 50, x: -2 },
      { time_ms: 100, x: 2 },
      { time_ms: 150, x: -2 },
      { time_ms: 200, x: 2 },
      { time_ms: 250, x: 0 },
    ],
    easing: 'linear',
    trigger: 'on_incorrect',
  };
}

/**
 * Create pulse animation motion path for correct placements.
 */
export function createPulseMotionPath(assetId: string): MotionPath {
  return {
    asset_id: assetId,
    keyframes: [
      { time_ms: 0, scale: 1.0 },
      { time_ms: 200, scale: 1.1 },
      { time_ms: 400, scale: 1.0 },
    ],
    easing: 'ease-in-out',
    trigger: 'on_complete',
  };
}

// =============================================================================
// Animation Timeline (GSAP-inspired sequencing)
// =============================================================================

interface TimelineEntry {
  animation: AnimationSpec;
  element?: HTMLElement | null;
  position: number; // Start time in ms
  duration: number;
  options?: AnimationTimelineOptions;
}

interface AnimationTimelineOptions {
  onStart?: () => void;
  onComplete?: () => void;
  stagger?: number; // Delay between repeated elements
}

interface TimelineControls {
  play: () => Promise<void>;
  pause: () => void;
  resume: () => void;
  stop: () => void;
  seek: (timeMs: number) => void;
  isPlaying: () => boolean;
  getDuration: () => number;
}

/**
 * AnimationTimeline - GSAP-style animation sequencing
 *
 * Allows chaining animations with precise timing control:
 * - add(animation, position): Add at absolute position
 * - addAfter(animation): Add after previous animation ends
 * - addWith(animation): Add at same time as previous animation
 *
 * Example:
 * ```
 * const timeline = new AnimationTimeline();
 * timeline
 *   .add(fadeInZone, 0)           // Start at 0ms
 *   .addAfter(pulseZone)          // Start when fadeIn ends
 *   .addWith(glowZone)            // Start at same time as pulse
 *   .add(bounceLabel, 500)        // Start at 500ms absolute
 *   .play();
 * ```
 */
export class AnimationTimeline {
  private entries: TimelineEntry[] = [];
  private currentPosition: number = 0;
  private isPaused: boolean = false;
  private isRunning: boolean = false;
  private startTime: number = 0;
  private pausedAt: number = 0;
  private animationFrameId: number | null = null;
  private runningAnimations: Map<HTMLElement, Animation> = new Map();
  private onCompleteCallback?: () => void;

  /**
   * Add animation at absolute position (in ms)
   */
  add(
    animation: AnimationSpec,
    position: number,
    element?: HTMLElement | null,
    options?: AnimationTimelineOptions
  ): this {
    const duration = animation.duration_ms + (animation.delay_ms || 0);
    this.entries.push({
      animation,
      element,
      position,
      duration,
      options,
    });
    this.currentPosition = position + duration;
    return this;
  }

  /**
   * Add animation to start after the previous animation ends
   */
  addAfter(
    animation: AnimationSpec,
    element?: HTMLElement | null,
    options?: AnimationTimelineOptions
  ): this {
    return this.add(animation, this.currentPosition, element, options);
  }

  /**
   * Add animation to start at the same time as the previous animation
   */
  addWith(
    animation: AnimationSpec,
    element?: HTMLElement | null,
    options?: AnimationTimelineOptions
  ): this {
    // Find the start position of the last entry
    const lastEntry = this.entries[this.entries.length - 1];
    const position = lastEntry ? lastEntry.position : 0;
    const duration = animation.duration_ms + (animation.delay_ms || 0);

    this.entries.push({
      animation,
      element,
      position,
      duration,
      options,
    });

    // Update current position to the max of current and new end time
    this.currentPosition = Math.max(this.currentPosition, position + duration);
    return this;
  }

  /**
   * Add animation with relative offset from current position
   * Positive offset: delay after current position
   * Negative offset: overlap with previous animation
   */
  addRelative(
    animation: AnimationSpec,
    offsetMs: number,
    element?: HTMLElement | null,
    options?: AnimationTimelineOptions
  ): this {
    const position = Math.max(0, this.currentPosition + offsetMs);
    return this.add(animation, position, element, options);
  }

  /**
   * Set callback for when timeline completes
   */
  onComplete(callback: () => void): this {
    this.onCompleteCallback = callback;
    return this;
  }

  /**
   * Get total timeline duration
   */
  getDuration(): number {
    if (this.entries.length === 0) return 0;
    return Math.max(...this.entries.map((e) => e.position + e.duration));
  }

  /**
   * Play the timeline
   */
  async play(): Promise<void> {
    if (this.isRunning) return;

    this.isRunning = true;
    this.isPaused = false;
    this.startTime = performance.now();
    const totalDuration = this.getDuration();

    // Inject all required keyframes
    const uniqueTypes = new Set(this.entries.map((e) => e.animation.type));
    uniqueTypes.forEach((type) => injectKeyframes(type));

    return new Promise((resolve) => {
      const tick = (currentTime: number) => {
        if (!this.isRunning) {
          resolve();
          return;
        }

        if (this.isPaused) {
          this.animationFrameId = requestAnimationFrame(tick);
          return;
        }

        const elapsed = currentTime - this.startTime;

        // Start animations that should begin at this time
        for (const entry of this.entries) {
          if (
            entry.element &&
            elapsed >= entry.position &&
            !this.runningAnimations.has(entry.element)
          ) {
            // Start this animation
            entry.options?.onStart?.();

            const { animation, element } = entry;
            const duration = animation.duration_ms / 1000;
            const delay = (animation.delay_ms || 0) / 1000;
            const easing = EASING_MAP[animation.easing] || 'ease-out';

            // Set CSS variables
            if (animation.color) {
              element.style.setProperty('--glow-color', animation.color);
              element.style.setProperty('--animation-color', animation.color);
            }

            // Apply animation via Web Animations API for better control
            const keyframes = this.getKeyframesForType(animation.type);
            const anim = element.animate(keyframes, {
              duration: animation.duration_ms,
              delay: animation.delay_ms || 0,
              easing,
              fill: 'forwards',
            });

            this.runningAnimations.set(element, anim);

            anim.onfinish = () => {
              this.runningAnimations.delete(element);
              entry.options?.onComplete?.();
            };
          }
        }

        // Check if timeline is complete
        if (elapsed >= totalDuration && this.runningAnimations.size === 0) {
          this.isRunning = false;
          this.onCompleteCallback?.();
          resolve();
          return;
        }

        this.animationFrameId = requestAnimationFrame(tick);
      };

      this.animationFrameId = requestAnimationFrame(tick);
    });
  }

  /**
   * Pause the timeline
   */
  pause(): void {
    if (!this.isRunning || this.isPaused) return;
    this.isPaused = true;
    this.pausedAt = performance.now();

    // Pause all running animations
    this.runningAnimations.forEach((anim) => anim.pause());
  }

  /**
   * Resume the timeline
   */
  resume(): void {
    if (!this.isPaused) return;
    this.isPaused = false;

    // Adjust start time to account for pause duration
    const pauseDuration = performance.now() - this.pausedAt;
    this.startTime += pauseDuration;

    // Resume all running animations
    this.runningAnimations.forEach((anim) => anim.play());
  }

  /**
   * Stop and reset the timeline
   */
  stop(): void {
    this.isRunning = false;
    this.isPaused = false;

    if (this.animationFrameId) {
      cancelAnimationFrame(this.animationFrameId);
      this.animationFrameId = null;
    }

    // Cancel all running animations
    this.runningAnimations.forEach((anim) => anim.cancel());
    this.runningAnimations.clear();
  }

  /**
   * Clear all entries and reset
   */
  clear(): this {
    this.stop();
    this.entries = [];
    this.currentPosition = 0;
    return this;
  }

  /**
   * Check if timeline is currently playing
   */
  isPlaying(): boolean {
    return this.isRunning && !this.isPaused;
  }

  /**
   * Get keyframes for animation type (Web Animations API format)
   */
  private getKeyframesForType(type: AnimationType): Keyframe[] {
    const keyframesMap: Record<AnimationType, Keyframe[]> = {
      pulse: [
        { transform: 'scale(1)', opacity: 1, offset: 0 },
        { transform: 'scale(1.1)', opacity: 0.8, offset: 0.5 },
        { transform: 'scale(1)', opacity: 1, offset: 1 },
      ],
      glow: [
        { boxShadow: '0 0 5px var(--glow-color, #3b82f6)', offset: 0 },
        { boxShadow: '0 0 20px var(--glow-color, #3b82f6), 0 0 30px var(--glow-color, #3b82f6)', offset: 0.5 },
        { boxShadow: '0 0 5px var(--glow-color, #3b82f6)', offset: 1 },
      ],
      scale: [
        { transform: 'scale(1)', offset: 0 },
        { transform: 'scale(1.15)', offset: 0.5 },
        { transform: 'scale(1)', offset: 1 },
      ],
      shake: [
        { transform: 'translateX(0)', offset: 0 },
        { transform: 'translateX(-5px)', offset: 0.1 },
        { transform: 'translateX(5px)', offset: 0.2 },
        { transform: 'translateX(-5px)', offset: 0.3 },
        { transform: 'translateX(5px)', offset: 0.4 },
        { transform: 'translateX(-5px)', offset: 0.5 },
        { transform: 'translateX(5px)', offset: 0.6 },
        { transform: 'translateX(-5px)', offset: 0.7 },
        { transform: 'translateX(5px)', offset: 0.8 },
        { transform: 'translateX(-5px)', offset: 0.9 },
        { transform: 'translateX(0)', offset: 1 },
      ],
      fade: [
        { opacity: 0, offset: 0 },
        { opacity: 1, offset: 1 },
      ],
      bounce: [
        { transform: 'translateY(0)', offset: 0 },
        { transform: 'translateY(0)', offset: 0.2 },
        { transform: 'translateY(-15px)', offset: 0.4 },
        { transform: 'translateY(0)', offset: 0.5 },
        { transform: 'translateY(-8px)', offset: 0.6 },
        { transform: 'translateY(0)', offset: 0.8 },
        { transform: 'translateY(0)', offset: 1 },
      ],
      confetti: [
        { opacity: 1, transform: 'translateY(0) rotate(0deg)', offset: 0 },
        { opacity: 0, transform: 'translateY(-50px) rotate(720deg)', offset: 1 },
      ],
      path_draw: [
        { strokeDashoffset: 1000, offset: 0 },
        { strokeDashoffset: 0, offset: 1 },
      ],
    };

    return keyframesMap[type] || keyframesMap.fade;
  }
}

/**
 * Hook for using AnimationTimeline
 */
export function useAnimationTimeline() {
  const timelineRef = useRef<AnimationTimeline | null>(null);

  const createTimeline = useCallback(() => {
    // Clean up previous timeline
    if (timelineRef.current) {
      timelineRef.current.stop();
    }
    timelineRef.current = new AnimationTimeline();
    return timelineRef.current;
  }, []);

  const getTimeline = useCallback(() => {
    if (!timelineRef.current) {
      timelineRef.current = new AnimationTimeline();
    }
    return timelineRef.current;
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (timelineRef.current) {
        timelineRef.current.stop();
      }
    };
  }, []);

  return {
    createTimeline,
    getTimeline,
  };
}
