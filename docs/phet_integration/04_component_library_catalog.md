# Open-Source Component Library Catalog for GamED.AI

This catalog documents all researched open-source libraries that can be leveraged for educational game development, organized by category with licensing, commercial use, and integration details.

## Quick Reference: Best Libraries by Use Case

| Use Case | Recommended Library | License | npm Package |
|----------|-------------------|---------|-------------|
| **Physics (2D)** | Matter.js | MIT | `matter-js` |
| **Physics (3D)** | Cannon.js | MIT | `cannon` |
| **Math Graphing** | JSXGraph | MIT/LGPL | `jsxgraph` |
| **Math Rendering** | KaTeX | MIT | `katex` |
| **Chemistry (Molecules)** | 3Dmol.js | BSD | `3dmol` |
| **Chemistry (Structures)** | Kekule.js | MIT | `kekule` |
| **Drag & Drop** | dnd-kit | MIT | `@dnd-kit/core` |
| **Animation** | Framer Motion | MIT | `framer-motion` |
| **Audio (Effects)** | Howler.js | MIT | `howler` |
| **Audio (Music)** | Tone.js | MIT | `tone` |
| **Game Framework** | Phaser | MIT | `phaser` |
| **Data Visualization** | D3.js | ISC | `d3` |
| **3D Graphics** | Three.js | MIT | `three` |
| **Maps/Geography** | Leaflet | BSD-2 | `leaflet` |
| **3D Globe** | CesiumJS | Apache 2.0 | `cesium` |

---

## 1. SIMULATION & PHYSICS ENGINES

### Matter.js ⭐ RECOMMENDED
**2D Physics Engine**

```bash
npm install matter-js
```

- **License:** MIT ✅
- **Commercial Use:** Yes, unlimited
- **Features:**
  - Rigid body physics
  - Collision detection
  - Constraints & springs
  - Excellent for educational physics demos
- **Integration:** Easy - works with any renderer
- **Docs:** https://brm.io/matter-js/

### Planck.js
**2D Physics (Box2D rewrite)**

```bash
npm install planck
```

- **License:** MIT ✅
- **Commercial Use:** Yes
- **Features:**
  - TypeScript rewrite of Box2D
  - Optimized for HTML5 games
  - Cross-platform compatibility
- **Best For:** Physics simulations needing Box2D compatibility

### Cannon.js ⭐ RECOMMENDED
**3D Physics Engine**

```bash
npm install cannon
```

- **License:** MIT ✅
- **Commercial Use:** Yes
- **Features:**
  - Lightweight 3D physics
  - Native JavaScript (not a port)
  - Excellent Three.js integration
- **Integration:** Pairs perfectly with Three.js

### Ammo.js
**Bullet Physics Port**

```bash
npm install ammo.js
```

- **License:** Zlib ✅
- **Commercial Use:** Yes
- **Features:**
  - Full Bullet physics via WebAssembly
  - Soft body dynamics (cloth, rope)
  - Most powerful 3D physics option
- **Trade-off:** Larger bundle size (~1MB)

---

## 2. MATHEMATICS & GRAPHING

### JSXGraph ⭐ RECOMMENDED
**Interactive Geometry & Graphing**

```bash
npm install jsxgraph
```

- **License:** MIT/LGPL (dual) ✅
- **Commercial Use:** Yes
- **Features:**
  - Interactive geometry
  - Function plotting
  - Only ~200KB
  - MathJax/KaTeX integration
  - Multi-touch support
- **Best For:** Interactive math exploration

### Mafs
**React Math Components**

```bash
npm install mafs
```

- **License:** MIT ✅
- **Commercial Use:** Yes
- **Features:**
  - Declarative React components
  - Interactive mathematical scenes
  - Built-in animations
- **Best For:** React-based math visualizations

### KaTeX ⭐ RECOMMENDED
**Fast Math Typesetting**

```bash
npm install katex
```

- **License:** MIT ✅
- **Commercial Use:** Yes
- **Features:**
  - Fastest math rendering
  - No dependencies
  - Based on TeX
- **Use For:** Rendering equations in games

### MathJax
**Full Math Rendering**

```html
<script src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>
```

- **License:** Apache 2.0 ✅
- **Commercial Use:** Yes
- **Features:**
  - LaTeX, MathML, AsciiMath input
  - Screen reader accessible
  - Server-side rendering support
- **Use For:** Complex mathematical notation

### Desmos API
**Graphing Calculator**

```html
<script src="https://www.desmos.com/api/v1.9/calculator.js?apiKey=YOUR_KEY"></script>
```

- **License:** Proprietary (free tier) ✅
- **Commercial Use:** Yes (free)
- **Features:**
  - Professional graphing calculator
  - 3D graphing
  - Geometry tools
- **Note:** Requires API key (free)

### GeoGebra
**Dynamic Mathematics**

```bash
npm install react-geogebra
```

- **License:** EUPL v1.2 ⚠️
- **Commercial Use:** Free for education; check terms for commercial
- **Features:**
  - Complete math platform
  - Geometry, algebra, calculus
  - Large community
- **Note:** License requires review for commercial products

---

## 3. CHEMISTRY VISUALIZATION

### 3Dmol.js ⭐ RECOMMENDED
**Molecular Viewer**

```bash
npm install 3dmol
```

- **License:** BSD ✅
- **Commercial Use:** Yes
- **Features:**
  - PDB, SDF, MOL2, XYZ formats
  - Multiple visualization styles
  - Interactive molecular data
  - Surface computation
- **Best For:** 3D molecular visualization

### Kekule.js ⭐ RECOMMENDED
**Chemical Structure Editor**

```bash
npm install kekule
```

- **License:** MIT ✅
- **Commercial Use:** Yes
- **Features:**
  - Draw/edit molecule structures
  - Chemoinformatics toolkit
  - Structure comparison/search
- **Best For:** Interactive chemistry editors

### RDKit.js
**Cheminformatics**

```bash
npm install @rdkit/rdkit
```

- **License:** BSD-3 ✅
- **Commercial Use:** Yes
- **Features:**
  - WebAssembly-based
  - Molecule rendering
  - Descriptor computation
- **Best For:** Advanced cheminformatics

### ChemDoodle Web
- **License:** GPLv3 ⚠️
- **Commercial Use:** Requires separate license
- **Note:** Great features but GPL restrictions

---

## 4. BIOLOGY & ANATOMY

### BioJS
**Biological Visualization Components**

```bash
npm install biojs-vis-sequence  # Example component
```

- **License:** MIT ✅
- **Commercial Use:** Yes
- **Features:**
  - Modular component registry
  - Sequence visualization
  - Standardized APIs
- **Best For:** Bioinformatics visualizations

### Open Anatomy Project
- **License:** Open Access ✅
- **Commercial Use:** Yes (educational)
- **Features:**
  - WebGL anatomy atlases
  - Three.js based
  - Collaborative viewing
- **URL:** https://www.openanatomy.org/

---

## 5. ANIMATION LIBRARIES

### Framer Motion ⭐ RECOMMENDED
**React Animation**

```bash
npm install framer-motion
```

- **License:** MIT ✅
- **Commercial Use:** Yes
- **Features:**
  - 12M+ monthly downloads
  - Gesture recognition
  - Layout animations
  - TypeScript support
- **Best For:** React-based games

### GSAP
**Professional Animation**

```bash
npm install gsap
```

- **License:** GreenSock Standard ✅
- **Commercial Use:** Yes (free tier)
- **Features:**
  - Industry standard
  - High performance
  - Extensive plugins
- **Note:** Some plugins require paid license

### Anime.js
**Lightweight Animation**

```bash
npm install animejs
```

- **License:** MIT ✅
- **Commercial Use:** Yes
- **Features:**
  - Only ~17KB
  - CSS, SVG, DOM animation
  - Tree-shakeable
- **Best For:** Simple, lightweight animations

### React Spring
**Physics-Based Animation**

```bash
npm install @react-spring/web
```

- **License:** MIT ✅
- **Commercial Use:** Yes
- **Features:**
  - Spring physics
  - Cross-platform (DOM, Native, Three.js)
  - Natural motion
- **Best For:** Natural-feeling UI animations

### Lottie
**After Effects Animations**

```bash
npm install lottie-react
```

- **License:** MIT ✅
- **Commercial Use:** Yes
- **Features:**
  - Parse AE animations
  - 10,000+ free animations on LottieFiles
  - Lightweight rendering
- **Best For:** Complex pre-made animations

### Rive
**Interactive Animations**

```bash
npm install @rive-app/react-canvas
```

- **License:** MIT (runtime) ✅
- **Commercial Use:** Yes
- **Features:**
  - State machines
  - 120fps rendering
  - Interactive design tool
- **Best For:** Complex interactive animations

---

## 6. AUDIO LIBRARIES

### Howler.js ⭐ RECOMMENDED
**Game Audio**

```bash
npm install howler
```

- **License:** MIT ✅
- **Commercial Use:** Yes
- **Features:**
  - Web Audio API + HTML5 fallback
  - Audio sprites
  - Volume, pan, fade
- **Best For:** Game sound effects

### Tone.js ⭐ RECOMMENDED
**Interactive Music**

```bash
npm install tone
```

- **License:** MIT ✅
- **Commercial Use:** Yes
- **Features:**
  - Synthesizers and effects
  - Musical timing/scheduling
  - MIDI support
- **Best For:** Music-based educational games

---

## 7. DRAG & DROP

### dnd-kit ⭐ RECOMMENDED
**Modern React DnD**

```bash
npm install @dnd-kit/core @dnd-kit/sortable
```

- **License:** MIT ✅
- **Commercial Use:** Yes
- **Features:**
  - ~10KB minified
  - Zero dependencies
  - Accessible by design
  - Multiple sensors (touch, keyboard)
- **Best For:** All React drag-drop needs

### interact.js
**Framework-Agnostic Gestures**

```bash
npm install interactjs
```

- **License:** MIT ✅
- **Commercial Use:** Yes
- **Features:**
  - Drag, drop, resize
  - Multi-touch gestures
  - Inertia and snapping
- **Best For:** Non-React projects

---

## 8. GAME FRAMEWORKS

### Phaser ⭐ RECOMMENDED
**2D Game Framework**

```bash
npm install phaser
```

- **License:** MIT ✅
- **Commercial Use:** Yes (completely free)
- **Features:**
  - Canvas/WebGL rendering
  - Built-in physics
  - Tilemap support
  - Animation system
  - Audio management
- **Best For:** Full game development

### p5.js
**Creative Coding**

```bash
npm install p5
```

- **License:** LGPL 2.1 ✅
- **Commercial Use:** Yes
- **Features:**
  - Beginner-friendly
  - Processing paradigm
  - Great for education
- **Best For:** Creative coding, simple simulations

---

## 9. 3D & VISUALIZATION

### Three.js ⭐ RECOMMENDED
**3D Graphics**

```bash
npm install three
```

- **License:** MIT ✅
- **Commercial Use:** Yes
- **Features:**
  - WebGL abstraction
  - Huge ecosystem
  - Extensive examples
- **Best For:** Any 3D visualization

### D3.js ⭐ RECOMMENDED
**Data Visualization**

```bash
npm install d3
```

- **License:** ISC ✅
- **Commercial Use:** Yes
- **Features:**
  - Most powerful viz library
  - Modular (500+ modules)
  - SVG, Canvas, HTML
- **Best For:** Data-driven educational content

### Spline
**3D Design Tool**

```bash
npm install @splinetool/react-spline
```

- **License:** Proprietary (free tier) ✅
- **Commercial Use:** Yes
- **Features:**
  - Browser-based 3D editor
  - Event handling
  - Next.js SSR support
- **Best For:** Quick 3D interactive elements

---

## 10. GEOGRAPHY & EARTH SCIENCE

### Leaflet ⭐ RECOMMENDED
**Interactive Maps**

```bash
npm install leaflet react-leaflet
```

- **License:** BSD-2 ✅
- **Commercial Use:** Yes (attribution required)
- **Features:**
  - Only 42KB
  - Mobile-friendly
  - GeoJSON support
- **Best For:** 2D map visualizations

### CesiumJS
**3D Globe**

```bash
npm install cesium
```

- **License:** Apache 2.0 ✅
- **Commercial Use:** Yes
- **Features:**
  - 3D globe visualization
  - Terrain/imagery streaming
  - 3D Tiles support
- **Best For:** Earth science, geography

### deck.gl
**Large-Scale Geo Visualization**

```bash
npm install deck.gl
```

- **License:** MIT ✅
- **Commercial Use:** Yes
- **Features:**
  - WebGL2-powered
  - Large dataset handling
  - Layer-based architecture
- **Best For:** Data-heavy geography

---

## 11. CIRCUIT SIMULATION

### CircuitJS
- **License:** GPLv2 ⚠️
- **Commercial Use:** Requires source disclosure
- **Features:**
  - Browser-based circuit sim
  - Offline versions available
- **URL:** https://www.falstad.com/circuit/

### Wokwi
- **License:** Proprietary ⚠️
- **Commercial Use:** Paid plans required
- **Features:**
  - Arduino/ESP32 simulation
  - VS Code integration
  - Custom chips API
- **URL:** https://wokwi.com/

---

## 12. GAME ASSETS

### Kenney Assets ⭐ RECOMMENDED
- **License:** CC0 (Public Domain) ✅
- **Commercial Use:** Yes, unlimited
- **Content:** 60,000+ 2D/3D assets, audio, fonts
- **URL:** https://kenney.nl/

### OpenGameArt.org
- **License:** Varies (CC0, CC-BY, CC-BY-SA) ✅
- **Commercial Use:** Yes
- **Content:** Community-verified game art
- **URL:** https://opengameart.org/

### Game-Icons.net
- **License:** CC 3.0 BY ✅
- **Commercial Use:** Yes (attribution)
- **Content:** 4,000+ SVG icons
- **URL:** https://game-icons.net/

---

## A2UI (Google)
**Agent-Driven User Interfaces**

- **License:** Apache 2.0 ✅
- **Commercial Use:** Yes
- **Features:**
  - Declarative JSON format for AI-generated UIs
  - Framework-agnostic renderers
  - Security-first approach
  - Dynamic data collection
- **URL:** https://github.com/google/A2UI
- **Status:** Early-stage (v0.8)
- **Best For:** AI agent-generated educational interfaces

---

## Integration Priority for GamED.AI

### Tier 1: Essential (Integrate First)
1. **Matter.js** - Physics simulations
2. **JSXGraph** - Math graphing
3. **KaTeX** - Math rendering
4. **dnd-kit** - Drag-drop interactions
5. **Howler.js** - Audio feedback
6. **Framer Motion** - UI animations

### Tier 2: Domain-Specific
1. **3Dmol.js** - Chemistry
2. **Three.js** - 3D visualizations
3. **Leaflet** - Geography
4. **Tone.js** - Music education

### Tier 3: Advanced Features
1. **Phaser** - Complex game templates
2. **CesiumJS** - Earth science
3. **D3.js** - Data visualization
4. **Rive** - Complex animations

---

## License Compatibility Matrix

| License | Commercial OK | Can Modify | Must Open Source | Attribution |
|---------|--------------|------------|------------------|-------------|
| MIT | ✅ | ✅ | ❌ | ✅ |
| Apache 2.0 | ✅ | ✅ | ❌ | ✅ |
| BSD | ✅ | ✅ | ❌ | ✅ |
| ISC | ✅ | ✅ | ❌ | ✅ |
| LGPL | ✅ | ✅ | Only modifications | ✅ |
| CC0 | ✅ | ✅ | ❌ | ❌ |
| CC-BY | ✅ | ✅ | ❌ | ✅ |
| GPL | ⚠️ | ✅ | ✅ Entire project | ✅ |

**Recommendation:** Prioritize MIT, Apache 2.0, BSD, and CC0 licensed libraries for maximum commercial flexibility.
