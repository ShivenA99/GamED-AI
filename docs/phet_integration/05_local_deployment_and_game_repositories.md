# PhET Local Deployment & Reusable Game Repositories

This document provides complete instructions for running PhET simulations locally without any external API dependency, plus a catalog of open-source game repositories you can extract components from.

---

## Part 1: Running PhET 100% Locally (No External API)

### Quick Answer: YES, PhET Works Fully Offline!

PhET HTML5 simulations are **completely self-contained** single HTML files with:
- ✅ No external API calls
- ✅ No CDN dependencies
- ✅ No internet required after download
- ✅ Works from `file://` URLs
- ✅ All assets embedded in single file

---

### Method 1: Direct Download (Easiest)

1. Go to any simulation: https://phet.colorado.edu/en/simulations
2. Click the **download arrow icon** below the simulation
3. Save the `.html` file locally
4. Open directly in browser - works offline!

**Example URLs for direct download:**
```
https://phet.colorado.edu/sims/html/projectile-motion/latest/projectile-motion_all.html
https://phet.colorado.edu/sims/html/circuit-construction-kit-dc/latest/circuit-construction-kit-dc_all.html
https://phet.colorado.edu/sims/html/states-of-matter/latest/states-of-matter_all.html
```

---

### Method 2: Bulk Download via GitHub Releases

Each simulation has pre-built releases on GitHub:

```bash
# Example: Download Projectile Motion
curl -L -o projectile-motion.html \
  https://github.com/phetsims/projectile-motion/releases/latest/download/projectile-motion_all.html

# Example: Download Circuit Construction Kit
curl -L -o circuit-kit.html \
  https://github.com/phetsims/circuit-construction-kit-dc/releases/latest/download/circuit-construction-kit-dc_all.html
```

**Repository pattern:** `https://github.com/phetsims/{simulation-name}/releases`

---

### Method 3: PhET Offline Installer (All Simulations)

Download complete PhET website (~1-2 GB):

**Windows/Mac/Linux:**
https://phet.colorado.edu/en/offline-access

After installation:
1. Navigate to installed folder
2. Open `index.html`
3. Access ALL simulations offline

---

### Method 4: Build From Source (Full Control)

```bash
# 1. Setup
mkdir phetsims && cd phetsims
git clone https://github.com/phetsims/perennial
cd perennial && npm install

# 2. Sync all repositories (this takes a while)
grunt sync

# 3. Build a specific simulation
cd ../projectile-motion
npm install
grunt

# Output: build/projectile-motion_all.html
```

**Prerequisites:**
- Node.js 18+
- npm
- Git
- Grunt CLI: `npm install -g grunt-cli`

---

### Self-Hosting Options

**Option A: Simple HTTP Server**
```bash
# Python
python -m http.server 8000

# Node.js
npx http-server ./simulations -p 8000

# Access at: http://localhost:8000/projectile-motion.html
```

**Option B: Nginx Configuration**
```nginx
server {
    listen 80;
    server_name simulations.local;
    root /var/www/phet-simulations;

    location / {
        try_files $uri $uri/ =404;
    }
}
```

**Option C: Docker**
```dockerfile
FROM nginx:alpine
COPY ./simulations /usr/share/nginx/html
EXPOSE 80
```

---

## Part 2: Complete PhET Simulation Catalog

### Physics Simulations (35+)

| Simulation | GitHub Repo | Concepts | Complexity |
|------------|-------------|----------|------------|
| **Projectile Motion** | [projectile-motion](https://github.com/phetsims/projectile-motion) | Kinematics, vectors, trajectory | Medium |
| **Circuit Construction Kit: DC** | [circuit-construction-kit-dc](https://github.com/phetsims/circuit-construction-kit-dc) | Circuits, Ohm's law, current | Medium |
| **Forces and Motion: Basics** | [forces-and-motion-basics](https://github.com/phetsims/forces-and-motion-basics) | Force, friction, motion | Easy |
| **Energy Skate Park** | [energy-skate-park](https://github.com/phetsims/energy-skate-park) | Energy conservation, KE, PE | Medium |
| **Waves** | [waves](https://github.com/phetsims/waves) | Wave properties, interference | Medium |
| **Friction** | [friction](https://github.com/phetsims/friction) | Forces, Newton's laws | Easy |
| **Pendulum Lab** | [pendulum-lab](https://github.com/phetsims/pendulum-lab) | Period, harmonic motion | Medium |
| **Gas Properties** | [gas-properties](https://github.com/phetsims/gas-properties) | Ideal gas law, kinetics | Medium |
| **Balloons and Static Electricity** | [balloons-and-static-electricity](https://github.com/phetsims/balloons-and-static-electricity) | Charge, electrostatics | Easy |
| **Coulomb's Law** | [coulombs-law](https://github.com/phetsims/coulombs-law) | Electric force | Medium |
| **Faraday's Law** | [faradays-law](https://github.com/phetsims/faradays-law) | Electromagnetic induction | Medium |
| **Charges and Fields** | [charges-and-fields](https://github.com/phetsims/charges-and-fields) | Electric fields | Medium |
| **Gravity Force Lab** | [gravity-force-lab](https://github.com/phetsims/gravity-force-lab) | Gravitational force | Medium |
| **Vector Addition** | [vector-addition](https://github.com/phetsims/vector-addition) | Vector math | Medium |
| **Masses and Springs** | [masses-and-springs](https://github.com/phetsims/masses-and-springs) | Hooke's law, oscillation | Medium |
| **Buoyancy** | [buoyancy](https://github.com/phetsims/buoyancy) | Archimedes principle | Hard |
| **Geometric Optics** | [geometric-optics](https://github.com/phetsims/geometric-optics) | Lenses, mirrors | Hard |
| **Blackbody Spectrum** | [blackbody-spectrum](https://github.com/phetsims/blackbody-spectrum) | Radiation, temperature | Hard |
| **Photoelectric Effect** | [photoelectric-effect](https://github.com/phetsims/photoelectric-effect) | Quantum physics | Hard |

### Chemistry Simulations (20+)

| Simulation | GitHub Repo | Concepts | Complexity |
|------------|-------------|----------|------------|
| **Build an Atom** | [build-an-atom](https://github.com/phetsims/build-an-atom) | Atomic structure | Easy |
| **Molecule Shapes** | [molecule-shapes](https://github.com/phetsims/molecule-shapes) | VSEPR, geometry | Medium |
| **Molecule Polarity** | [molecule-polarity](https://github.com/phetsims/molecule-polarity) | Electronegativity, dipole | Medium |
| **States of Matter** | [states-of-matter](https://github.com/phetsims/states-of-matter) | Phase transitions | Medium |
| **pH Scale** | [ph-scale](https://github.com/phetsims/ph-scale) | Acids, bases, pH | Easy |
| **Concentration** | [concentration](https://github.com/phetsims/concentration) | Molarity, solutions | Medium |
| **Isotopes and Atomic Mass** | [isotopes-and-atomic-mass](https://github.com/phetsims/isotopes-and-atomic-mass) | Nuclear chemistry | Medium |
| **Build a Molecule** | [build-a-molecule](https://github.com/phetsims/build-a-molecule) | Molecular structure | Easy |
| **Acid-Base Solutions** | [acid-base-solutions](https://github.com/phetsims/acid-base-solutions) | Equilibrium, strength | Hard |
| **Reactants Products Leftovers** | [reactants-products-and-leftovers](https://github.com/phetsims/reactants-products-and-leftovers) | Stoichiometry | Medium |
| **Balancing Chemical Equations** | [balancing-chemical-equations](https://github.com/phetsims/balancing-chemical-equations) | Conservation of mass | Medium |
| **Rutherford Scattering** | [rutherford-scattering](https://github.com/phetsims/rutherford-scattering) | Nuclear structure | Hard |

### Mathematics Simulations (15+)

| Simulation | GitHub Repo | Concepts | Complexity |
|------------|-------------|----------|------------|
| **Graphing Quadratics** | [graphing-quadratics](https://github.com/phetsims/graphing-quadratics) | Parabolas, vertex | Medium |
| **Graphing Lines** | [graphing-lines](https://github.com/phetsims/graphing-lines) | Linear equations, slope | Easy |
| **Area Builder** | [area-builder](https://github.com/phetsims/area-builder) | Geometry, area | Easy |
| **Fractions Intro** | [fractions-intro](https://github.com/phetsims/fractions-intro) | Fractions, equivalence | Easy |
| **Number Line Integers** | [number-line-integers](https://github.com/phetsims/number-line-integers) | Integers, comparison | Easy |
| **Calculus Grapher** | [calculus-grapher](https://github.com/phetsims/calculus-grapher) | Derivatives, integrals | Hard |
| **Plinko Probability** | [plinko-probability](https://github.com/phetsims/plinko-probability) | Statistics, probability | Medium |
| **Mean Share and Balance** | [mean-share-and-balance](https://github.com/phetsims/mean-share-and-balance) | Mean, distribution | Easy |
| **Function Builder** | [function-builder](https://github.com/phetsims/function-builder) | Functions, transformations | Medium |

### Biology Simulations (8+)

| Simulation | GitHub Repo | Concepts | Complexity |
|------------|-------------|----------|------------|
| **Natural Selection** | [natural-selection](https://github.com/phetsims/natural-selection) | Evolution, mutation | Medium |
| **Gene Expression Essentials** | [gene-expression-essentials](https://github.com/phetsims/gene-expression-essentials) | DNA, protein synthesis | Hard |
| **Neuron** | [neuron](https://github.com/phetsims/neuron) | Action potential | Hard |
| **Membrane Transport** | [membrane-transport](https://github.com/phetsims/membrane-transport) | Diffusion, channels | Medium |

### Earth Science Simulations (5+)

| Simulation | GitHub Repo | Concepts | Complexity |
|------------|-------------|----------|------------|
| **Greenhouse Effect** | [greenhouse-effect](https://github.com/phetsims/greenhouse-effect) | Climate, radiation | Medium |
| **Plate Tectonics** | [plate-tectonics](https://github.com/phetsims/plate-tectonics) | Geology, earthquakes | Medium |

---

## Part 3: Reusable Game Code Repositories

### Tier 1: Best for Component Extraction (MIT Licensed)

#### Physics Game Engines

| Repository | License | Stars | Tech | Reusable Components |
|------------|---------|-------|------|---------------------|
| [matter-js](https://github.com/liabru/matter-js) | MIT | 16k+ | JS | Physics engine, collision, constraints |
| [planck.js](https://github.com/piqnt/planck.js) | MIT | 4.8k | TS | Box2D port, joints, sensors |
| [cannon-es](https://github.com/pmndrs/cannon-es) | MIT | 1.8k | TS | 3D physics, rigid bodies |
| [p2.js](https://github.com/schteppe/p2.js) | MIT | 2.6k | JS | 2D physics, springs, motors |

**Matter.js Complete Game Examples:**
```
https://github.com/liabru/matter-js/tree/master/examples
├── airFriction.js
├── avalanche.js
├── ballPool.js
├── bridge.js
├── car.js
├── catapult.js
├── chains.js
├── circleStack.js
├── cloth.js
├── collisionFiltering.js
├── compositeManipulation.js
├── compound.js
├── concave.js
├── constraints.js
├── doublePendulum.js
├── friction.js
├── gravity.js
├── gyro.js
├── manipulation.js
├── mixed.js
├── newtonsCradle.js
├── ragdoll.js
├── restitution.js
├── rounded.js
├── sensors.js
├── sleeping.js
├── slingshot.js
├── softBody.js
├── sprites.js
├── stack.js
├── staticFriction.js
├── stress.js
├── stress2.js
├── timescale.js
└── wreckingBall.js
```

#### Game Frameworks with Examples

| Repository | License | Stars | Complete Games Included |
|------------|---------|-------|------------------------|
| [phaser](https://github.com/phaserjs/phaser) | MIT | 37k+ | 1000+ examples |
| [GDevelop](https://github.com/4ian/GDevelop) | MIT | 12k+ | Full game engine |
| [kaboom](https://github.com/replit/kaboom) | MIT | 3k+ | Snake, Mario, RPG examples |
| [excalibur](https://github.com/excaliburjs/Excalibur) | BSD-2 | 1.6k | TypeScript game engine |

**Phaser Example Games (Full Source):**
```
https://github.com/phaserjs/phaser3-examples
├── games/
│   ├── breakout/           # Classic breakout
│   ├── firstgame/          # Platformer tutorial
│   ├── invaders/           # Space invaders
│   └── tank/               # Tank game
├── physics/
│   ├── arcade/             # Arcade physics examples
│   ├── matterjs/           # Matter.js integration
│   └── impact/             # Impact physics
└── input/
    ├── dragging/           # Drag and drop
    └── gamepad/            # Controller support
```

#### Educational Game Repositories

| Repository | License | Tech | Type |
|------------|---------|------|------|
| [KhanQuest](https://github.com/Khan/KhanQuest) | MIT | JS | Math RPG game |
| [Scratch](https://github.com/scratchfoundation/scratch-gui) | BSD-3 | React | Visual programming |
| [Snap](https://github.com/jmoenig/Snap) | AGPL | JS | Block programming |
| [PuzzleScript](https://github.com/increpare/PuzzleScript) | MIT | JS | Puzzle game engine |

---

### Tier 2: Simulation-Specific Repositories

#### Math Visualization

| Repository | License | Use Case |
|------------|---------|----------|
| [jsxgraph](https://github.com/jsxgraph/jsxgraph) | MIT/LGPL | Interactive geometry |
| [mafs](https://github.com/stevenpetryk/mafs) | MIT | React math components |
| [desmos-api](https://www.desmos.com/api) | Free | Graphing calculator |
| [function-plot](https://github.com/mauriciopoppe/function-plot) | MIT | Function plotting |
| [mathbox](https://github.com/unconed/mathbox) | MIT | 3D math visualization |

**JSXGraph Examples:**
```javascript
// Interactive geometry
const board = JXG.JSXGraph.initBoard('box', {boundingbox: [-5, 5, 5, -5]});
const p1 = board.create('point', [0, 0], {name: 'A'});
const p2 = board.create('point', [2, 2], {name: 'B'});
const line = board.create('line', [p1, p2]);
const circle = board.create('circle', [p1, 2]);
```

#### Chemistry Visualization

| Repository | License | Use Case |
|------------|---------|----------|
| [3Dmol.js](https://github.com/3dmol/3Dmol.js) | BSD | 3D molecules |
| [Kekule.js](https://github.com/partridgejiang/Kekule.js) | MIT | Structure editor |
| [rdkit-js](https://github.com/rdkit/rdkit-js) | BSD-3 | Cheminformatics |
| [molstar](https://github.com/molstar/molstar) | MIT | Macromolecules |

**3Dmol.js Example:**
```javascript
// Embed molecule viewer
let viewer = $3Dmol.createViewer('container', {backgroundColor: 'white'});
viewer.addModel(pdbData, 'pdb');
viewer.setStyle({}, {cartoon: {color: 'spectrum'}});
viewer.zoomTo();
viewer.render();
```

#### Circuit Simulation

| Repository | License | Notes |
|------------|---------|-------|
| [circuitjs1](https://github.com/sharpie7/circuitjs1) | GPL-2 | Full circuit sim |
| [logisim-evolution](https://github.com/logisim-evolution/logisim-evolution) | GPL-3 | Digital logic |
| [Digital](https://github.com/hneemann/Digital) | GPL-3 | Logic simulator |

⚠️ **Note:** Circuit simulators are mostly GPL - requires open-sourcing if modified.

---

### Tier 3: Drag-and-Drop & UI Components

| Repository | License | Use Case |
|------------|---------|----------|
| [@dnd-kit/core](https://github.com/clauderic/dnd-kit) | MIT | React DnD |
| [react-beautiful-dnd](https://github.com/atlassian/react-beautiful-dnd) | Apache-2 | List reordering |
| [interact.js](https://github.com/taye/interact.js) | MIT | Gestures, drag |
| [Sortable](https://github.com/SortableJS/Sortable) | MIT | Sortable lists |

**dnd-kit Example for GamED.AI:**
```tsx
import {DndContext, useDraggable, useDroppable} from '@dnd-kit/core';

function DraggableLabel({id, children}) {
  const {attributes, listeners, setNodeRef, transform} = useDraggable({id});
  return (
    <div ref={setNodeRef} {...listeners} {...attributes}>
      {children}
    </div>
  );
}

function DropZone({id, children}) {
  const {setNodeRef, isOver} = useDroppable({id});
  return (
    <div ref={setNodeRef} className={isOver ? 'highlight' : ''}>
      {children}
    </div>
  );
}
```

---

### Tier 4: Animation & Audio

#### Animation

| Repository | License | Best For |
|------------|---------|----------|
| [framer-motion](https://github.com/framer/motion) | MIT | React animations |
| [anime.js](https://github.com/juliangarnier/anime) | MIT | Lightweight (17KB) |
| [gsap](https://github.com/greensock/GSAP) | Standard | Professional |
| [lottie-web](https://github.com/airbnb/lottie-web) | MIT | After Effects |
| [rive-react](https://github.com/rive-app/rive-react) | MIT | Interactive |

#### Audio

| Repository | License | Best For |
|------------|---------|----------|
| [howler.js](https://github.com/goldfire/howler.js) | MIT | Sound effects |
| [tone.js](https://github.com/Tonejs/Tone.js) | MIT | Music synthesis |
| [pizzicato](https://github.com/alemangui/pizzicato) | MIT | Audio effects |

---

## Part 4: Recommended Architecture for GamED.AI

### Component Stack (All MIT Licensed)

```
GamED.AI Simulation Engine
├── Physics Layer
│   ├── Matter.js (2D) ─────── Projectile motion, friction, collisions
│   └── Cannon-es (3D) ─────── 3D physics simulations
│
├── Math Layer
│   ├── JSXGraph ───────────── Interactive geometry/graphing
│   ├── KaTeX ──────────────── Equation rendering
│   └── Mafs ───────────────── React math components
│
├── Chemistry Layer
│   ├── 3Dmol.js ───────────── 3D molecular viewer
│   └── Kekule.js ──────────── Structure editor
│
├── Interaction Layer
│   ├── dnd-kit ────────────── Drag and drop
│   ├── Framer Motion ──────── Animations
│   └── interact.js ────────── Gestures
│
├── Audio Layer
│   ├── Howler.js ──────────── Sound effects
│   └── Tone.js ────────────── Music/synthesis
│
└── Rendering Layer
    ├── Three.js ───────────── 3D graphics
    ├── PixiJS ─────────────── 2D WebGL
    └── D3.js ──────────────── Data visualization
```

### Example: Building Projectile Motion Without PhET

```tsx
// Using Matter.js + React
import Matter from 'matter-js';
import { useEffect, useRef, useState } from 'react';

function ProjectileSimulation({ angle, velocity }) {
  const canvasRef = useRef();
  const engineRef = useRef();

  useEffect(() => {
    const engine = Matter.Engine.create();
    const render = Matter.Render.create({
      canvas: canvasRef.current,
      engine: engine,
      options: { width: 800, height: 400 }
    });

    // Ground
    const ground = Matter.Bodies.rectangle(400, 390, 800, 20, { isStatic: true });

    // Projectile
    const vx = velocity * Math.cos(angle * Math.PI / 180);
    const vy = -velocity * Math.sin(angle * Math.PI / 180);
    const projectile = Matter.Bodies.circle(50, 350, 10, {
      restitution: 0.6,
      friction: 0.1
    });
    Matter.Body.setVelocity(projectile, { x: vx, y: vy });

    Matter.Composite.add(engine.world, [ground, projectile]);
    Matter.Render.run(render);
    Matter.Runner.run(Matter.Runner.create(), engine);

    engineRef.current = engine;
    return () => {
      Matter.Render.stop(render);
      Matter.Engine.clear(engine);
    };
  }, [angle, velocity]);

  return <canvas ref={canvasRef} />;
}
```

---

## Part 5: Download Scripts

### Bulk Download PhET Simulations

```bash
#!/bin/bash
# download_phet_simulations.sh

SIMULATIONS=(
  "projectile-motion"
  "circuit-construction-kit-dc"
  "states-of-matter"
  "graphing-quadratics"
  "friction"
  "pendulum-lab"
  "build-an-atom"
  "molecule-polarity"
  "natural-selection"
  "energy-skate-park"
)

mkdir -p phet_simulations

for sim in "${SIMULATIONS[@]}"; do
  echo "Downloading $sim..."
  curl -L -o "phet_simulations/${sim}.html" \
    "https://phet.colorado.edu/sims/html/${sim}/latest/${sim}_all.html"
done

echo "Done! All simulations saved to phet_simulations/"
```

### Clone PhET Source Repositories

```bash
#!/bin/bash
# clone_phet_sources.sh

REPOS=(
  "projectile-motion"
  "circuit-construction-kit-dc"
  "states-of-matter"
  "graphing-quadratics"
  "scenery"
  "axon"
  "sun"
  "joist"
)

mkdir -p phet_source

for repo in "${REPOS[@]}"; do
  echo "Cloning $repo..."
  git clone "https://github.com/phetsims/${repo}.git" "phet_source/${repo}"
done

echo "Done! All repositories cloned to phet_source/"
```

---

## Summary

### PhET Local Usage: Key Points

1. **100% Offline** - Download HTML files, run locally
2. **No API Required** - Self-contained single files
3. **Source Available** - All 85+ simulations on GitHub
4. **Build Yourself** - Full build system documented
5. **License: CC BY 4.0** - Free for commercial use with attribution

### Best Repositories for Component Extraction

| Priority | Repository | Why |
|----------|------------|-----|
| 1 | Matter.js | Best 2D physics, extensive examples |
| 2 | JSXGraph | Interactive math, MIT licensed |
| 3 | Phaser | Complete game framework, 1000+ examples |
| 4 | dnd-kit | Modern React drag-drop |
| 5 | 3Dmol.js | Chemistry visualization |
| 6 | SceneryStack | PhET's own component library (MIT) |

### License Summary

| Source | License | Commercial Use |
|--------|---------|----------------|
| PhET Simulations | CC BY 4.0 | ✅ Yes (attribution) |
| PhET Source Code | MIT/GPL | ✅ MIT parts, ⚠️ GPL parts |
| SceneryStack | MIT | ✅ Yes |
| Matter.js | MIT | ✅ Yes |
| Phaser | MIT | ✅ Yes |
| JSXGraph | MIT/LGPL | ✅ Yes |
