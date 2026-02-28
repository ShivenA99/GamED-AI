# GamED.AI PhET Bridge

This directory contains the tools for building and integrating PhET Interactive Simulations with GamED.AI's assessment framework.

## Contents

- `gamed-bridge.js` - JavaScript bridge module that gets injected into PhET simulations
- `build-simulations.sh` - Build script for cloning, building, and injecting the bridge
- `dist/simulations/` - Output directory for built simulations (created by build script)

## Quick Start

### Prerequisites

- Node.js v18+
- npm
- Git
- grunt-cli (`npm install -g grunt-cli`)

### Building All Simulations

```bash
./build-simulations.sh
```

### Building a Specific Simulation

```bash
./build-simulations.sh projectile-motion
```

### Building Multiple Specific Simulations

```bash
./build-simulations.sh projectile-motion states-of-matter gas-properties
```

## Bridge Module API

The bridge module enables communication between the GamED.AI frontend and the PhET simulation via postMessage.

### Messages FROM Parent (Commands)

Send messages to the simulation iframe:

```javascript
iframe.contentWindow.postMessage({
  target: 'phet-gamed-bridge',
  command: 'track-property',
  params: { path: 'model.cannonAngleProperty' },
  requestId: 'unique-id-123'
}, '*');
```

#### Available Commands

| Command | Params | Description |
|---------|--------|-------------|
| `get-state` | none | Get all tracked property values |
| `set-property` | `{ path, value }` | Set a property value |
| `track-property` | `{ path, alias? }` | Start tracking a property |
| `untrack-property` | `{ path }` | Stop tracking a property |
| `track-properties-batch` | `{ properties: [{path, alias}] }` | Track multiple properties |
| `reset` | none | Reset the simulation |
| `get-interactions` | `{ since?, limit? }` | Get interaction log |
| `clear-interactions` | none | Clear interaction log |
| `get-property-value` | `{ path }` | Get a single property value |
| `change-screen` | `{ screenIndex }` | Change active screen |
| `ping` | none | Check if bridge is alive |

### Messages TO Parent (Events)

Listen for messages from the simulation:

```javascript
window.addEventListener('message', (event) => {
  if (event.data.source !== 'phet-gamed-bridge') return;

  switch (event.data.type) {
    case 'bridge-ready':
      console.log('Simulation loaded:', event.data.data);
      break;
    case 'property-changed':
      console.log('Property changed:', event.data.data);
      break;
    case 'interaction':
      console.log('User interaction:', event.data.data);
      break;
  }
});
```

#### Event Types

| Type | Data | Description |
|------|------|-------------|
| `bridge-ready` | `{ name, version, screens }` | Simulation loaded and ready |
| `bridge-error` | `{ error }` | Bridge initialization failed |
| `state-snapshot` | `{ state, timestamp }` | Current state of all tracked properties |
| `property-changed` | `{ path, value, oldValue, timestamp }` | Property value changed |
| `property-set` | `{ path, success, error? }` | Property set result |
| `track-confirmed` | `{ path, success, initialValue? }` | Tracking started |
| `untrack-confirmed` | `{ path, success }` | Tracking stopped |
| `interaction` | `{ type, details, timestamp }` | User interaction occurred |
| `interactions` | `{ log, total }` | Interaction log response |
| `reset-complete` | `{ success }` | Simulation reset complete |

## Property Paths

Property paths follow this format:
- `model.propertyName` - Property on current screen's model
- `view.propertyName` - Property on current screen's view
- `screenName.model.propertyName` - Property on specific screen

### Examples by Simulation

**Projectile Motion:**
```javascript
// Track cannon angle
{ path: 'model.cannonAngleProperty', alias: 'angle' }

// Track launch speed
{ path: 'model.initialSpeedProperty', alias: 'speed' }
```

**States of Matter:**
```javascript
// Track temperature
{ path: 'model.temperatureSetPointProperty', alias: 'temperature' }

// Track phase
{ path: 'model.phaseProperty', alias: 'phase' }
```

**Gas Properties:**
```javascript
// Track pressure
{ path: 'model.pressureProperty', alias: 'pressure' }

// Track volume
{ path: 'model.volumeProperty', alias: 'volume' }
```

## Hosting the Built Simulations

After building, serve the `dist/simulations` directory with a static file server:

```bash
# Using Python
cd dist/simulations
python -m http.server 8080

# Using Node.js
npx serve dist/simulations

# Using nginx (example config)
location /simulations/ {
    alias /path/to/dist/simulations/;
    add_header Access-Control-Allow-Origin *;
}
```

Then embed in your application:

```html
<iframe
  src="http://localhost:8080/projectile-motion/projectile-motion_gamed.html"
  width="800"
  height="600"
  allow="fullscreen">
</iframe>
```

## Troubleshooting

### Build Fails with "Module not found"

Ensure all core dependencies are cloned. Run with verbose logging:

```bash
DEBUG=1 ./build-simulations.sh projectile-motion
```

### Bridge Not Initializing

Check browser console for errors. The bridge waits up to 10 seconds for the simulation to load.

### Properties Not Found

Use the simulation's tandem structure. Enable debug mode in the bridge:

```javascript
// In gamed-bridge.js
const CONFIG = {
  DEBUG: true,  // Enable debug logging
  ...
};
```

## Attribution

Based on PhET Interactive Simulations, University of Colorado Boulder.
https://phet.colorado.edu

Licensed under CC BY 4.0. When using these simulations, include proper attribution to PhET.
