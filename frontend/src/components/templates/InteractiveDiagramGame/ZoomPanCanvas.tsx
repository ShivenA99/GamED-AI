'use client';

import { useRef, useState, useCallback } from 'react';
import { TransformWrapper, TransformComponent, ReactZoomPanPinchRef } from 'react-zoom-pan-pinch';

interface ZoomPanCanvasProps {
  children: React.ReactNode;
  /** Enable zoom/pan */
  enabled?: boolean;
  /** Minimum zoom level */
  minZoom?: number;
  /** Maximum zoom level */
  maxZoom?: number;
  /** Initial zoom level */
  initialZoom?: number;
  /** Show minimap */
  showMinimap?: boolean;
  /** Show zoom controls */
  showControls?: boolean;
  /** Canvas width for minimap ratio */
  canvasWidth?: number;
  /** Canvas height for minimap ratio */
  canvasHeight?: number;
  /** Disable panning during drag operations */
  disablePanOnDrag?: boolean;
}

function ZoomControls({
  onZoomIn,
  onZoomOut,
  onReset,
  currentZoom,
}: {
  onZoomIn: () => void;
  onZoomOut: () => void;
  onReset: () => void;
  currentZoom: number;
}) {
  return (
    <div className="absolute top-3 right-3 flex flex-col gap-1 z-20">
      <button
        onClick={onZoomIn}
        className="w-8 h-8 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg shadow-sm hover:bg-gray-50 dark:hover:bg-gray-600 flex items-center justify-center text-gray-700 dark:text-gray-200 transition-colors"
        aria-label="Zoom in"
        title="Zoom in"
      >
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v12M6 12h12" />
        </svg>
      </button>

      <div className="text-center text-xs text-gray-500 dark:text-gray-400 bg-white dark:bg-gray-700 rounded px-1 py-0.5 border border-gray-200 dark:border-gray-600">
        {Math.round(currentZoom * 100)}%
      </div>

      <button
        onClick={onZoomOut}
        className="w-8 h-8 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg shadow-sm hover:bg-gray-50 dark:hover:bg-gray-600 flex items-center justify-center text-gray-700 dark:text-gray-200 transition-colors"
        aria-label="Zoom out"
        title="Zoom out"
      >
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 12h12" />
        </svg>
      </button>

      <button
        onClick={onReset}
        className="w-8 h-8 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg shadow-sm hover:bg-gray-50 dark:hover:bg-gray-600 flex items-center justify-center text-gray-700 dark:text-gray-200 transition-colors mt-1"
        aria-label="Reset zoom"
        title="Fit to view"
      >
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4" />
        </svg>
      </button>
    </div>
  );
}

export default function ZoomPanCanvas({
  children,
  enabled = true,
  minZoom = 0.5,
  maxZoom = 3,
  initialZoom = 1,
  showControls = true,
  disablePanOnDrag = true,
}: ZoomPanCanvasProps) {
  const transformRef = useRef<ReactZoomPanPinchRef>(null);
  const [currentZoom, setCurrentZoom] = useState(initialZoom);
  const [isPanning, setIsPanning] = useState(false);

  const handleZoomIn = useCallback(() => {
    transformRef.current?.zoomIn(0.3);
  }, []);

  const handleZoomOut = useCallback(() => {
    transformRef.current?.zoomOut(0.3);
  }, []);

  const handleReset = useCallback(() => {
    transformRef.current?.resetTransform();
  }, []);

  if (!enabled) {
    return <div className="relative">{children}</div>;
  }

  return (
    <div className="relative overflow-hidden rounded-lg">
      <TransformWrapper
        ref={transformRef}
        initialScale={initialZoom}
        minScale={minZoom}
        maxScale={maxZoom}
        centerOnInit
        wheel={{ step: 0.1 }}
        pinch={{ step: 5 }}
        doubleClick={{ mode: 'reset' }}
        panning={{
          disabled: isPanning && disablePanOnDrag,
          velocityDisabled: true,
        }}
        onTransformed={(_, state) => {
          setCurrentZoom(state.scale);
        }}
        onPanningStart={() => setIsPanning(true)}
        onPanningStop={() => setIsPanning(false)}
      >
        <TransformComponent
          wrapperStyle={{ width: '100%', height: '100%' }}
          contentStyle={{ width: '100%', height: '100%' }}
        >
          {children}
        </TransformComponent>
      </TransformWrapper>

      {/* Zoom controls */}
      {showControls && (
        <ZoomControls
          onZoomIn={handleZoomIn}
          onZoomOut={handleZoomOut}
          onReset={handleReset}
          currentZoom={currentZoom}
        />
      )}

      {/* Zoom hint on first load */}
      {currentZoom === initialZoom && (
        <div className="absolute bottom-3 left-3 text-xs text-gray-400 dark:text-gray-500 bg-white/80 dark:bg-gray-800/80 px-2 py-1 rounded backdrop-blur-sm z-10 pointer-events-none">
          Scroll to zoom • Double-click to reset
        </div>
      )}
    </div>
  );
}
