/**
 * GamED.AI PhET Bridge Module
 *
 * This module is injected into self-hosted PhET simulations to enable
 * communication between the simulation and the GamED.AI assessment framework.
 *
 * Features:
 * - Property tracking and state change notifications
 * - User interaction logging
 * - State snapshots and restoration
 * - Remote property manipulation
 *
 * @version 1.0.0
 * @license MIT
 */

(function() {
  'use strict';

  // Configuration
  const CONFIG = {
    VERSION: '1.0.0',
    POLL_INTERVAL: 100, // ms to wait for simulation load
    MAX_POLL_ATTEMPTS: 100, // Max attempts before giving up
    INTERACTION_BUFFER_SIZE: 1000, // Max interactions to keep in memory
    DEBUG: false // Set to true for console logging
  };

  // Internal state
  const state = {
    initialized: false,
    sim: null,
    trackedProperties: new Map(),
    interactionLog: [],
    propertySnapshots: new Map(),
    lastSnapshotTime: 0
  };

  // Utility: Debug logger
  function log(...args) {
    if (CONFIG.DEBUG) {
      console.log('[GamED Bridge]', ...args);
    }
  }

  // Utility: Send message to parent window
  function sendToParent(type, data) {
    const message = {
      source: 'phet-gamed-bridge',
      version: CONFIG.VERSION,
      type: type,
      data: data,
      timestamp: Date.now()
    };

    try {
      window.parent.postMessage(message, '*');
      log('Sent:', type, data);
    } catch (e) {
      console.error('[GamED Bridge] Failed to send message:', e);
    }
  }

  // Wait for simulation to load
  function waitForSimulation() {
    let attempts = 0;

    const pollInterval = setInterval(() => {
      attempts++;

      // Check for PhET simulation object
      if (window.phet && window.phet.joist && window.phet.joist.sim) {
        clearInterval(pollInterval);
        initializeBridge(window.phet.joist.sim);
      } else if (attempts >= CONFIG.MAX_POLL_ATTEMPTS) {
        clearInterval(pollInterval);
        sendToParent('bridge-error', {
          error: 'Simulation failed to load within timeout',
          attempts: attempts
        });
      }
    }, CONFIG.POLL_INTERVAL);
  }

  // Initialize the bridge once simulation is ready
  function initializeBridge(sim) {
    if (state.initialized) return;

    state.sim = sim;
    state.initialized = true;

    // Extract simulation info
    const simInfo = extractSimulationInfo(sim);

    // Set up message listener
    window.addEventListener('message', handleIncomingMessage);

    // Set up interaction tracking
    setupInteractionTracking(sim);

    // Announce ready
    sendToParent('bridge-ready', simInfo);

    log('Initialized for:', simInfo.name);
  }

  // Extract simulation metadata
  function extractSimulationInfo(sim) {
    const screens = sim.screens || [];

    return {
      name: sim.simNameProperty ? sim.simNameProperty.value : 'unknown',
      version: sim.version || 'unknown',
      screens: screens.map((screen, index) => ({
        index: index,
        name: getScreenName(screen, index),
        hasModel: !!screen.model,
        hasView: !!screen.view
      })),
      currentScreenIndex: sim.screenIndexProperty ? sim.screenIndexProperty.value : 0
    };
  }

  // Get screen name safely
  function getScreenName(screen, index) {
    if (screen.nameProperty && screen.nameProperty.value) {
      return screen.nameProperty.value;
    }
    if (screen.tandem && screen.tandem.phetioID) {
      const parts = screen.tandem.phetioID.split('.');
      return parts[parts.length - 1] || `Screen ${index + 1}`;
    }
    return `Screen ${index + 1}`;
  }

  // Handle incoming messages from parent
  function handleIncomingMessage(event) {
    const data = event.data;

    // Validate message
    if (!data || data.target !== 'phet-gamed-bridge') return;

    const { command, params, requestId } = data;

    log('Received command:', command, params);

    try {
      switch (command) {
        case 'get-state':
          handleGetState(requestId);
          break;
        case 'set-property':
          handleSetProperty(params, requestId);
          break;
        case 'track-property':
          handleTrackProperty(params, requestId);
          break;
        case 'untrack-property':
          handleUntrackProperty(params, requestId);
          break;
        case 'track-properties-batch':
          handleTrackPropertiesBatch(params, requestId);
          break;
        case 'reset':
          handleReset(requestId);
          break;
        case 'get-interactions':
          handleGetInteractions(params, requestId);
          break;
        case 'clear-interactions':
          handleClearInteractions(requestId);
          break;
        case 'get-property-value':
          handleGetPropertyValue(params, requestId);
          break;
        case 'change-screen':
          handleChangeScreen(params, requestId);
          break;
        case 'ping':
          sendToParent('pong', { requestId });
          break;
        default:
          sendToParent('error', {
            requestId,
            error: `Unknown command: ${command}`
          });
      }
    } catch (e) {
      sendToParent('error', {
        requestId,
        error: e.message,
        stack: e.stack
      });
    }
  }

  // Resolve a property path to the actual property object
  function resolvePropertyPath(path) {
    if (!state.sim) return null;

    const parts = path.split('.');
    let current = null;

    // Determine starting point
    const firstPart = parts[0];

    // Check if it starts with a screen name or index
    if (firstPart.match(/Screen$/i) || firstPart.match(/^\d+$/)) {
      // Find screen by name or index
      const screenIndex = firstPart.match(/^\d+$/)
        ? parseInt(firstPart)
        : state.sim.screens.findIndex(s => {
            const name = getScreenName(s, -1);
            return name.toLowerCase().includes(firstPart.toLowerCase().replace('screen', ''));
          });

      if (screenIndex >= 0 && screenIndex < state.sim.screens.length) {
        current = state.sim.screens[screenIndex];
        parts.shift(); // Remove screen identifier
      }
    } else {
      // Default to current screen
      const currentIndex = state.sim.screenIndexProperty ? state.sim.screenIndexProperty.value : 0;
      current = state.sim.screens[currentIndex];
    }

    if (!current) return null;

    // Navigate the path
    for (const part of parts) {
      if (current === null || current === undefined) return null;

      // Try direct access
      if (current[part] !== undefined) {
        current = current[part];
      }
      // Try with 'Property' suffix
      else if (current[part + 'Property'] !== undefined) {
        current = current[part + 'Property'];
      }
      // Try case-insensitive match
      else {
        const keys = Object.keys(current);
        const match = keys.find(k => k.toLowerCase() === part.toLowerCase());
        if (match) {
          current = current[match];
        } else {
          return null;
        }
      }
    }

    return current;
  }

  // Get serializable value from a property
  function getPropertyValue(prop) {
    if (prop === null || prop === undefined) return null;

    // Handle Axon Property
    if (typeof prop.get === 'function') {
      return serializeValue(prop.get());
    }

    // Handle direct value property
    if (prop.value !== undefined) {
      return serializeValue(prop.value);
    }

    return serializeValue(prop);
  }

  // Serialize a value for postMessage
  function serializeValue(value) {
    if (value === null || value === undefined) return value;

    // Handle primitives
    if (typeof value === 'number' || typeof value === 'string' || typeof value === 'boolean') {
      return value;
    }

    // Handle Vector2
    if (value.x !== undefined && value.y !== undefined) {
      return { x: value.x, y: value.y };
    }

    // Handle Vector3
    if (value.x !== undefined && value.y !== undefined && value.z !== undefined) {
      return { x: value.x, y: value.y, z: value.z };
    }

    // Handle Bounds2
    if (value.minX !== undefined && value.minY !== undefined) {
      return {
        minX: value.minX,
        minY: value.minY,
        maxX: value.maxX,
        maxY: value.maxY
      };
    }

    // Handle enumerations
    if (value.name !== undefined) {
      return value.name;
    }

    // Handle arrays
    if (Array.isArray(value)) {
      return value.map(serializeValue);
    }

    // Default: try to convert to string
    try {
      return String(value);
    } catch (e) {
      return '[Complex Object]';
    }
  }

  // Handle get-state command
  function handleGetState(requestId) {
    const stateSnapshot = {};

    state.trackedProperties.forEach((info, path) => {
      stateSnapshot[path] = getPropertyValue(info.property);
    });

    sendToParent('state-snapshot', {
      requestId,
      state: stateSnapshot,
      timestamp: Date.now()
    });
  }

  // Handle set-property command
  function handleSetProperty(params, requestId) {
    const { path, value } = params;
    const prop = resolvePropertyPath(path);

    if (!prop) {
      sendToParent('property-set', {
        requestId,
        path,
        success: false,
        error: 'Property not found'
      });
      return;
    }

    try {
      if (typeof prop.set === 'function') {
        prop.set(value);
      } else if (prop.value !== undefined) {
        prop.value = value;
      } else {
        throw new Error('Property is not settable');
      }

      sendToParent('property-set', {
        requestId,
        path,
        value,
        success: true
      });
    } catch (e) {
      sendToParent('property-set', {
        requestId,
        path,
        success: false,
        error: e.message
      });
    }
  }

  // Handle track-property command
  function handleTrackProperty(params, requestId) {
    const { path, alias } = params;
    const prop = resolvePropertyPath(path);

    if (!prop) {
      sendToParent('track-confirmed', {
        requestId,
        path,
        success: false,
        error: 'Property not found'
      });
      return;
    }

    // Check if already tracking
    if (state.trackedProperties.has(path)) {
      sendToParent('track-confirmed', {
        requestId,
        path,
        success: true,
        alreadyTracking: true
      });
      return;
    }

    // Create listener
    const listener = (value, oldValue) => {
      const serializedValue = serializeValue(value);
      const serializedOldValue = serializeValue(oldValue);

      sendToParent('property-changed', {
        path,
        alias: alias || path,
        value: serializedValue,
        oldValue: serializedOldValue,
        timestamp: Date.now()
      });
    };

    // Attach listener
    if (typeof prop.link === 'function') {
      prop.link(listener);

      state.trackedProperties.set(path, {
        property: prop,
        listener: listener,
        alias: alias || path
      });

      sendToParent('track-confirmed', {
        requestId,
        path,
        alias: alias || path,
        success: true,
        initialValue: getPropertyValue(prop)
      });
    } else {
      sendToParent('track-confirmed', {
        requestId,
        path,
        success: false,
        error: 'Property does not support listeners'
      });
    }
  }

  // Handle untrack-property command
  function handleUntrackProperty(params, requestId) {
    const { path } = params;
    const info = state.trackedProperties.get(path);

    if (!info) {
      sendToParent('untrack-confirmed', {
        requestId,
        path,
        success: false,
        error: 'Property was not being tracked'
      });
      return;
    }

    // Remove listener
    if (typeof info.property.unlink === 'function') {
      info.property.unlink(info.listener);
    }

    state.trackedProperties.delete(path);

    sendToParent('untrack-confirmed', {
      requestId,
      path,
      success: true
    });
  }

  // Handle batch property tracking
  function handleTrackPropertiesBatch(params, requestId) {
    const { properties } = params;
    const results = [];

    for (const propConfig of properties) {
      const { path, alias } = propConfig;
      const prop = resolvePropertyPath(path);

      if (!prop) {
        results.push({ path, success: false, error: 'Property not found' });
        continue;
      }

      if (state.trackedProperties.has(path)) {
        results.push({ path, success: true, alreadyTracking: true });
        continue;
      }

      const listener = (value, oldValue) => {
        sendToParent('property-changed', {
          path,
          alias: alias || path,
          value: serializeValue(value),
          oldValue: serializeValue(oldValue),
          timestamp: Date.now()
        });
      };

      if (typeof prop.link === 'function') {
        prop.link(listener);
        state.trackedProperties.set(path, { property: prop, listener, alias: alias || path });
        results.push({ path, success: true, initialValue: getPropertyValue(prop) });
      } else {
        results.push({ path, success: false, error: 'Property does not support listeners' });
      }
    }

    sendToParent('track-batch-confirmed', { requestId, results });
  }

  // Handle reset command
  function handleReset(requestId) {
    if (state.sim && typeof state.sim.reset === 'function') {
      state.sim.reset();
      state.interactionLog.length = 0;

      sendToParent('reset-complete', { requestId, success: true });
    } else {
      sendToParent('reset-complete', {
        requestId,
        success: false,
        error: 'Reset not available'
      });
    }
  }

  // Handle get-interactions command
  function handleGetInteractions(params, requestId) {
    const { since, limit } = params || {};

    let interactions = state.interactionLog;

    if (since) {
      interactions = interactions.filter(i => i.timestamp > since);
    }

    if (limit) {
      interactions = interactions.slice(-limit);
    }

    sendToParent('interactions', {
      requestId,
      log: interactions,
      total: state.interactionLog.length
    });
  }

  // Handle clear-interactions command
  function handleClearInteractions(requestId) {
    state.interactionLog.length = 0;
    sendToParent('interactions-cleared', { requestId, success: true });
  }

  // Handle get-property-value command
  function handleGetPropertyValue(params, requestId) {
    const { path } = params;
    const prop = resolvePropertyPath(path);

    if (!prop) {
      sendToParent('property-value', {
        requestId,
        path,
        success: false,
        error: 'Property not found'
      });
      return;
    }

    sendToParent('property-value', {
      requestId,
      path,
      value: getPropertyValue(prop),
      success: true
    });
  }

  // Handle change-screen command
  function handleChangeScreen(params, requestId) {
    const { screenIndex } = params;

    if (!state.sim || !state.sim.screenIndexProperty) {
      sendToParent('screen-changed', {
        requestId,
        success: false,
        error: 'Screen navigation not available'
      });
      return;
    }

    if (screenIndex < 0 || screenIndex >= state.sim.screens.length) {
      sendToParent('screen-changed', {
        requestId,
        success: false,
        error: 'Invalid screen index'
      });
      return;
    }

    state.sim.screenIndexProperty.value = screenIndex;

    sendToParent('screen-changed', {
      requestId,
      screenIndex,
      success: true
    });
  }

  // Set up interaction tracking
  function setupInteractionTracking(sim) {
    // Track pointer events
    if (window.phet && window.phet.scenery && sim.display) {
      const display = sim.display;

      display.addInputListener({
        down: (event) => logInteraction('pointer-down', extractPointerData(event)),
        up: (event) => logInteraction('pointer-up', extractPointerData(event)),
        move: (event) => {
          // Throttle move events
          if (Date.now() - state.lastSnapshotTime > 100) {
            logInteraction('pointer-move', extractPointerData(event));
            state.lastSnapshotTime = Date.now();
          }
        }
      });
    }

    // Track screen changes
    if (sim.screenIndexProperty) {
      sim.screenIndexProperty.link((index, oldIndex) => {
        if (oldIndex !== null && oldIndex !== undefined) {
          logInteraction('screen-change', {
            from: oldIndex,
            to: index
          });
        }
      });
    }

    // Track reset button
    if (sim.screens) {
      sim.screens.forEach((screen, index) => {
        if (screen.view && screen.view.resetAllButton) {
          // This is a heuristic - reset button clicked
          const originalListener = screen.view.resetAllButton.buttonModel.isFiringProperty;
          if (originalListener && originalListener.link) {
            originalListener.link((isFiring) => {
              if (isFiring) {
                logInteraction('reset-all', { screenIndex: index });
              }
            });
          }
        }
      });
    }
  }

  // Extract pointer data from event
  function extractPointerData(event) {
    if (!event || !event.pointer) return {};

    return {
      x: event.pointer.point ? event.pointer.point.x : 0,
      y: event.pointer.point ? event.pointer.point.y : 0,
      type: event.pointer.type || 'unknown'
    };
  }

  // Log an interaction
  function logInteraction(type, details) {
    const interaction = {
      type,
      details,
      timestamp: Date.now()
    };

    state.interactionLog.push(interaction);

    // Trim buffer if too large
    if (state.interactionLog.length > CONFIG.INTERACTION_BUFFER_SIZE) {
      state.interactionLog.shift();
    }

    // Send to parent
    sendToParent('interaction', interaction);
  }

  // Start the bridge
  waitForSimulation();

  log('Bridge script loaded, waiting for simulation...');
})();
