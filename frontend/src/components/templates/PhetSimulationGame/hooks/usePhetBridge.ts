/**
 * usePhetBridge Hook
 *
 * Manages communication between GamED and PhET simulation iframe.
 * Handles state changes, interactions, and outcomes via postMessage API.
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { BridgeConfig, PhetInteraction, InteractionType } from '../types';

interface UsePhetBridgeOptions {
  bridgeConfig?: BridgeConfig;
  onStateChange?: (property: string, value: any, oldValue: any) => void;
  onInteraction?: (interaction: PhetInteraction) => void;
  onOutcome?: (outcomeId: string, value: any) => void;
  onReady?: () => void;
}

interface UsePhetBridgeReturn {
  iframeRef: React.RefObject<HTMLIFrameElement>;
  isReady: boolean;
  simulationState: Record<string, any>;
  interactions: PhetInteraction[];
  sendCommand: (command: string, payload?: any) => void;
  setProperty: (propertyName: string, value: any) => void;
  reset: () => void;
  getState: () => void;
}

export function usePhetBridge(options: UsePhetBridgeOptions): UsePhetBridgeReturn {
  const {
    bridgeConfig,
    onStateChange,
    onInteraction,
    onOutcome,
    onReady
  } = options;

  const iframeRef = useRef<HTMLIFrameElement>(null);
  const [isReady, setIsReady] = useState(false);
  const [simulationState, setSimulationState] = useState<Record<string, any>>({});
  const [interactions, setInteractions] = useState<PhetInteraction[]>([]);

  const messagePrefix = bridgeConfig?.messagePrefix || 'PHET_';

  // Handle incoming messages from the simulation
  const handleMessage = useCallback((event: MessageEvent) => {
    const data = event.data;

    // Validate message format
    if (!data || typeof data !== 'object') return;
    if (!data.type || typeof data.type !== 'string') return;
    if (!data.type.startsWith(messagePrefix)) return;

    // Check simulation ID matches (if provided)
    if (bridgeConfig?.simulationId && data.simulationId !== bridgeConfig.simulationId) {
      return;
    }

    const messageType = data.type.replace(messagePrefix, '');

    switch (messageType) {
      case 'BRIDGE_READY':
        setIsReady(true);
        onReady?.();
        break;

      case 'STATE_CHANGE':
        handleStateChange(data.property, data.value, data.previousValue);
        break;

      case 'STATE_BATCH':
        handleStateBatch(data.updates);
        break;

      case 'INTERACTION':
        handleInteractionEvent(data.interactionId, data.data, data.timestamp);
        break;

      case 'OUTCOME':
        handleOutcomeEvent(data.outcomeId, data.value, data.unit);
        break;

      case 'CURRENT_STATE':
        handleFullState(data.state);
        break;

      default:
        // Unknown message types are silently ignored in production
        // Enable DEBUG_PHET_BRIDGE env var to see unknown messages
        if (process.env.NODE_ENV === 'development') {
          // eslint-disable-next-line no-console
          console.debug(`[PhetBridge] Unknown message type: ${messageType}`, data);
        }
    }
  }, [bridgeConfig, messagePrefix, onReady]);

  // Handle single state change
  const handleStateChange = useCallback((property: string, value: any, oldValue: any) => {
    setSimulationState(prev => ({ ...prev, [property]: value }));
    onStateChange?.(property, value, oldValue);
  }, [onStateChange]);

  // Handle batched state updates
  const handleStateBatch = useCallback((updates: Record<string, { value: any; oldValue: any }>) => {
    setSimulationState(prev => {
      const newState = { ...prev };
      for (const [property, update] of Object.entries(updates)) {
        newState[property] = update.value;
        onStateChange?.(property, update.value, update.oldValue);
      }
      return newState;
    });
  }, [onStateChange]);

  // Handle interaction event
  const handleInteractionEvent = useCallback((
    interactionId: string,
    data?: Record<string, any>,
    timestamp?: number
  ) => {
    const interaction: PhetInteraction = {
      id: interactionId,
      type: data?.type as InteractionType || 'button_click',
      timestamp: timestamp || Date.now(),
      data
    };

    setInteractions(prev => [...prev, interaction]);
    onInteraction?.(interaction);
  }, [onInteraction]);

  // Handle outcome event
  const handleOutcomeEvent = useCallback((outcomeId: string, value: any, unit?: string) => {
    setSimulationState(prev => ({ ...prev, [outcomeId]: value }));
    onOutcome?.(outcomeId, value);
  }, [onOutcome]);

  // Handle full state update
  const handleFullState = useCallback((state: Record<string, any>) => {
    setSimulationState(state);
  }, []);

  // Send command to simulation
  const sendCommand = useCallback((command: string, payload?: any) => {
    if (!iframeRef.current?.contentWindow) {
      console.warn('[PhetBridge] Cannot send command - iframe not ready');
      return;
    }

    iframeRef.current.contentWindow.postMessage({
      type: `${messagePrefix}${command}`,
      ...payload
    }, '*');
  }, [messagePrefix]);

  // Set a property value in the simulation
  const setProperty = useCallback((propertyName: string, value: any) => {
    sendCommand('SET_PROPERTY', { property: propertyName, value });
  }, [sendCommand]);

  // Reset the simulation
  const reset = useCallback(() => {
    sendCommand('RESET');
    setInteractions([]);
    setSimulationState({});
  }, [sendCommand]);

  // Request current state from simulation
  const getState = useCallback(() => {
    sendCommand('GET_STATE');
  }, [sendCommand]);

  // Set up message listener
  useEffect(() => {
    window.addEventListener('message', handleMessage);
    return () => window.removeEventListener('message', handleMessage);
  }, [handleMessage]);

  // Set initial state when ready
  useEffect(() => {
    if (isReady && bridgeConfig?.initialState) {
      for (const [property, value] of Object.entries(bridgeConfig.initialState)) {
        setProperty(property, value);
      }
    }
  }, [isReady, bridgeConfig?.initialState, setProperty]);

  // Polling fallback for non-phetio simulations
  useEffect(() => {
    if (!bridgeConfig?.usePolling || !isReady) return;

    const pollInterval = setInterval(() => {
      getState();
    }, bridgeConfig.pollIntervalMs || 500);

    return () => clearInterval(pollInterval);
  }, [bridgeConfig?.usePolling, bridgeConfig?.pollIntervalMs, isReady, getState]);

  return {
    iframeRef,
    isReady,
    simulationState,
    interactions,
    sendCommand,
    setProperty,
    reset,
    getState
  };
}

/**
 * Get PhET simulation URL
 */
export function getPhetSimulationUrl(
  simulationId: string,
  localPath?: string,
  screen?: string
): string {
  // If local path provided, use it
  if (localPath) {
    return localPath;
  }

  // Otherwise, use PhET website
  let url = `https://phet.colorado.edu/sims/html/${simulationId}/latest/${simulationId}_all.html`;

  // Add screen parameter if specified
  if (screen) {
    url += `?screens=${screen}`;
  }

  return url;
}

/**
 * Check if a PhET simulation is available locally
 */
export async function checkLocalSimulation(localPath: string): Promise<boolean> {
  try {
    const response = await fetch(localPath, { method: 'HEAD' });
    return response.ok;
  } catch {
    return false;
  }
}
