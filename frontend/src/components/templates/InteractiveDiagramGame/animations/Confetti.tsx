'use client';

import { useEffect, useState, useCallback, useMemo, useRef } from 'react';
import { useReducedMotion } from '../hooks/useReducedMotion';

interface ConfettiPiece {
  id: number;
  x: number;
  y: number;
  color: string;
  rotation: number;
  scale: number;
  velocityX: number;
  velocityY: number;
  rotationSpeed: number;
  shape: 'square' | 'circle' | 'ribbon';
}

interface ConfettiProps {
  isActive: boolean;
  duration?: number;
  particleCount?: number;
  colors?: string[];
  gravity?: number;
  onComplete?: () => void;
}

const DEFAULT_COLORS = [
  '#f94144', // Red
  '#f3722c', // Orange
  '#f8961e', // Yellow-Orange
  '#f9c74f', // Yellow
  '#90be6d', // Light Green
  '#43aa8b', // Teal
  '#577590', // Blue-Gray
  '#4361ee', // Blue
  '#7209b7', // Purple
];

const SHAPES = ['square', 'circle', 'ribbon'] as const;

function createConfettiPiece(
  id: number,
  containerWidth: number,
  containerHeight: number,
  colors: string[]
): ConfettiPiece {
  return {
    id,
    x: Math.random() * containerWidth,
    y: -20 - Math.random() * 100, // Start above the container
    color: colors[Math.floor(Math.random() * colors.length)],
    rotation: Math.random() * 360,
    scale: 0.5 + Math.random() * 0.5,
    velocityX: (Math.random() - 0.5) * 8,
    velocityY: Math.random() * 3 + 2,
    rotationSpeed: (Math.random() - 0.5) * 15,
    shape: SHAPES[Math.floor(Math.random() * SHAPES.length)],
  };
}

/**
 * Optimized Confetti Component
 *
 * Uses refs for animation state to avoid React re-renders during the RAF loop.
 * DOM elements are updated directly for 60fps performance without reconciliation overhead.
 *
 * Accessibility: Respects prefers-reduced-motion media query.
 */
export default function Confetti({
  isActive,
  duration = 3000,
  particleCount = 50,
  colors = DEFAULT_COLORS,
  gravity = 0.3,
  onComplete,
}: ConfettiProps) {
  // Accessibility: Respect reduced motion preference
  const prefersReducedMotion = useReducedMotion();

  // Track whether animation is running (triggers mount/unmount)
  const [isAnimating, setIsAnimating] = useState(false);

  // Skip confetti entirely if user prefers reduced motion
  useEffect(() => {
    if (prefersReducedMotion && isActive && onComplete) {
      // Immediately call onComplete without animation
      onComplete();
    }
  }, [prefersReducedMotion, isActive, onComplete]);

  // Don't render anything if reduced motion is preferred
  if (prefersReducedMotion) {
    return null;
  }

  // Refs for animation state (no React re-renders during animation)
  const piecesRef = useRef<ConfettiPiece[]>([]);
  const containerRef = useRef<HTMLDivElement>(null);
  const pieceElementsRef = useRef<Map<number, HTMLDivElement>>(new Map());
  const animationIdRef = useRef<number | null>(null);
  const dimensionsRef = useRef({ width: 0, height: 0 });

  // Initialize dimensions
  useEffect(() => {
    if (typeof window !== 'undefined') {
      dimensionsRef.current = {
        width: window.innerWidth,
        height: window.innerHeight,
      };

      const handleResize = () => {
        dimensionsRef.current = {
          width: window.innerWidth,
          height: window.innerHeight,
        };
      };

      window.addEventListener('resize', handleResize);
      return () => window.removeEventListener('resize', handleResize);
    }
  }, []);

  // Start/stop animation when isActive changes
  useEffect(() => {
    if (isActive && dimensionsRef.current.width > 0) {
      // Initialize pieces
      const newPieces: ConfettiPiece[] = [];
      for (let i = 0; i < particleCount; i++) {
        newPieces.push(
          createConfettiPiece(i, dimensionsRef.current.width, dimensionsRef.current.height, colors)
        );
      }
      piecesRef.current = newPieces;
      pieceElementsRef.current.clear();
      setIsAnimating(true);
    } else {
      setIsAnimating(false);
      piecesRef.current = [];
      pieceElementsRef.current.clear();
    }
  }, [isActive, particleCount, colors]);

  // Animation loop using direct DOM manipulation (no React re-renders)
  useEffect(() => {
    if (!isAnimating) return;

    const startTime = performance.now();

    const animate = (currentTime: number) => {
      const elapsed = currentTime - startTime;

      if (elapsed >= duration) {
        piecesRef.current = [];
        pieceElementsRef.current.clear();
        setIsAnimating(false);
        onComplete?.();
        return;
      }

      // Update piece positions directly (mutate refs)
      const screenHeight = dimensionsRef.current.height;
      const activePieces: ConfettiPiece[] = [];

      for (const piece of piecesRef.current) {
        // Update physics
        piece.x += piece.velocityX;
        piece.y += piece.velocityY;
        piece.rotation += piece.rotationSpeed;
        piece.velocityY += gravity;
        piece.velocityX += (Math.random() - 0.5) * 0.2;

        // Keep pieces that haven't fallen off screen
        if (piece.y < screenHeight + 50) {
          activePieces.push(piece);

          // Update DOM element directly (bypasses React reconciliation)
          const element = pieceElementsRef.current.get(piece.id);
          if (element) {
            element.style.left = `${piece.x}px`;
            element.style.top = `${piece.y}px`;
            element.style.transform = `rotate(${piece.rotation}deg) scale(${piece.scale})`;
          }
        }
      }

      piecesRef.current = activePieces;

      // End animation if all pieces are gone
      if (activePieces.length === 0) {
        setIsAnimating(false);
        onComplete?.();
        return;
      }

      animationIdRef.current = requestAnimationFrame(animate);
    };

    animationIdRef.current = requestAnimationFrame(animate);

    return () => {
      if (animationIdRef.current) {
        cancelAnimationFrame(animationIdRef.current);
      }
    };
  }, [isAnimating, duration, gravity, onComplete]);

  // Register element refs for direct DOM manipulation
  const registerPieceRef = useCallback((id: number, element: HTMLDivElement | null) => {
    if (element) {
      pieceElementsRef.current.set(id, element);
    } else {
      pieceElementsRef.current.delete(id);
    }
  }, []);

  if (!isAnimating) return null;

  // Initial render - pieces are rendered once, then updated via direct DOM manipulation
  return (
    <div
      ref={containerRef}
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        width: '100%',
        height: '100%',
        pointerEvents: 'none',
        overflow: 'hidden',
        zIndex: 9999,
      }}
    >
      {piecesRef.current.map((piece) => (
        <div
          key={piece.id}
          ref={(el) => registerPieceRef(piece.id, el)}
          style={{
            position: 'absolute',
            left: piece.x,
            top: piece.y,
            transform: `rotate(${piece.rotation}deg) scale(${piece.scale})`,
            pointerEvents: 'none',
            zIndex: 9999,
            width: piece.shape === 'ribbon' ? 4 : piece.shape === 'circle' ? 8 : 10,
            height: piece.shape === 'ribbon' ? 16 : piece.shape === 'circle' ? 8 : 10,
            backgroundColor: piece.color,
            borderRadius: piece.shape === 'circle' ? '50%' : 2,
          }}
        />
      ))}
    </div>
  );
}

/**
 * Hook for controlling confetti
 */
export function useConfetti(defaultDuration = 3000) {
  const [isActive, setIsActive] = useState(false);
  const [duration, setDuration] = useState(defaultDuration);

  const trigger = useCallback((customDuration?: number) => {
    if (customDuration) {
      setDuration(customDuration);
    }
    setIsActive(true);
  }, []);

  const stop = useCallback(() => {
    setIsActive(false);
  }, []);

  const handleComplete = useCallback(() => {
    setIsActive(false);
  }, []);

  const ConfettiComponent = useMemo(
    () =>
      function ConfettiWrapper(props: Omit<ConfettiProps, 'isActive' | 'duration' | 'onComplete'>) {
        return (
          <Confetti
            {...props}
            isActive={isActive}
            duration={duration}
            onComplete={handleComplete}
          />
        );
      },
    [isActive, duration, handleComplete]
  );

  return {
    trigger,
    stop,
    isActive,
    Confetti: ConfettiComponent,
  };
}
