/**
 * Enhanced Visualization Components
 *
 * These components provide advanced visualization capabilities
 * for educational games using verified open-source libraries.
 *
 * All libraries have been verified for:
 * - MIT, BSD, or equivalent permissive licenses
 * - Active maintenance
 * - React compatibility
 */

// Physics simulation (Matter.js - MIT)
export { PhysicsSimulation } from './PhysicsSimulation'
export type { PhysicsBody, PhysicsSimulationProps } from './PhysicsSimulation'

// Mathematical graphing (SVG-based, extensible with Mafs/JSXGraph)
export { MathGraph } from './MathGraph'
export type { MathFunction, Point, MathGraphProps } from './MathGraph'

// 3D Molecular visualization (3Dmol.js - BSD)
export { MoleculeViewer } from './MoleculeViewer'
export type { MoleculeViewerProps } from './MoleculeViewer'

// Interactive maps (Leaflet - BSD-2)
export { InteractiveMap } from './InteractiveMap'
export type { MapMarker, MapRegion, InteractiveMapProps } from './InteractiveMap'

// Data visualization (SVG-based, extensible with Chart.js - MIT)
export { SimpleChart } from './SimpleChart'
export type { DataPoint, SimpleChartProps } from './SimpleChart'

/**
 * Library Installation Commands
 *
 * To enable full functionality of these components, install:
 *
 * Physics (Matter.js):
 *   npm install matter-js @types/matter-js
 *
 * Math Graphing (Mafs - React-native alternative):
 *   npm install mafs
 *
 * Molecular Visualization (3Dmol.js):
 *   npm install 3dmol
 *
 * Interactive Maps (Leaflet):
 *   npm install leaflet react-leaflet @types/leaflet
 *
 * Charts (Chart.js):
 *   npm install chart.js react-chartjs-2
 */
