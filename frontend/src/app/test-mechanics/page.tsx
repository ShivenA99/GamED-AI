'use client';

import { useState, useCallback } from 'react';
import dynamic from 'next/dynamic';
import {
  DndContext,
  DragStartEvent,
  DragEndEvent,
  MouseSensor,
  TouchSensor,
  useSensor,
  useSensors,
  closestCenter,
} from '@dnd-kit/core';
import type {
  InteractiveDiagramBlueprint,
  PlacedLabel,
  Label,
  MechanicAction,
  ActionResult,
} from '@/components/templates/InteractiveDiagramGame/types';

// Lazy load each enhanced component to test in isolation
const EnhancedDragDropGame = dynamic(
  () => import('@/components/templates/InteractiveDiagramGame/EnhancedDragDropGame'),
  { ssr: false },
);
const EnhancedSequenceBuilder = dynamic(
  () => import('@/components/templates/InteractiveDiagramGame/interactions/EnhancedSequenceBuilder'),
  { ssr: false },
);
const EnhancedSortingCategories = dynamic(
  () => import('@/components/templates/InteractiveDiagramGame/interactions/EnhancedSortingCategories'),
  { ssr: false },
);
const EnhancedMemoryMatch = dynamic(
  () => import('@/components/templates/InteractiveDiagramGame/interactions/EnhancedMemoryMatch').then(m => ({ default: m.EnhancedMemoryMatch })),
  { ssr: false },
);
const EnhancedHotspotManager = dynamic(
  () => import('@/components/templates/InteractiveDiagramGame/interactions/EnhancedHotspotManager').then(m => ({ default: m.EnhancedHotspotManager })),
  { ssr: false },
);
const EnhancedPathDrawer = dynamic(
  () => import('@/components/templates/InteractiveDiagramGame/interactions/EnhancedPathDrawer').then(m => ({ default: m.EnhancedPathDrawer })),
  { ssr: false },
);

// ─── Placeholder diagram SVG ─────────────────────────────────────
// A schematic heart diagram with clear zone positions
const HEART_DIAGRAM_SVG = 'data:image/svg+xml;base64,' + btoa(`
<svg xmlns="http://www.w3.org/2000/svg" width="800" height="600" viewBox="0 0 800 600">
  <defs>
    <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#f8fafc;stop-opacity:1" />
      <stop offset="100%" style="stop-color:#e2e8f0;stop-opacity:1" />
    </linearGradient>
    <linearGradient id="redGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#fca5a5;stop-opacity:0.3" />
      <stop offset="100%" style="stop-color:#ef4444;stop-opacity:0.15" />
    </linearGradient>
    <linearGradient id="blueGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#93c5fd;stop-opacity:0.3" />
      <stop offset="100%" style="stop-color:#3b82f6;stop-opacity:0.15" />
    </linearGradient>
  </defs>
  <rect width="800" height="600" fill="url(#bg)" rx="8"/>

  <!-- Heart outline -->
  <path d="M400,520 C250,520 120,400 120,260 C120,160 200,100 280,100 C340,100 380,140 400,180 C420,140 460,100 520,100 C600,100 680,160 680,260 C680,400 550,520 400,520Z"
    fill="#fef2f2" stroke="#dc2626" stroke-width="2.5" opacity="0.6"/>

  <!-- Septum (middle wall) -->
  <line x1="400" y1="150" x2="400" y2="480" stroke="#991b1b" stroke-width="3" stroke-dasharray="8,4" opacity="0.4"/>

  <!-- Left Atrium (top-left) -->
  <ellipse cx="290" cy="210" rx="90" ry="65" fill="url(#redGrad)" stroke="#dc2626" stroke-width="1.5"/>

  <!-- Right Atrium (top-right) -->
  <ellipse cx="510" cy="210" rx="90" ry="65" fill="url(#blueGrad)" stroke="#3b82f6" stroke-width="1.5"/>

  <!-- Left Ventricle (bottom-left) -->
  <ellipse cx="290" cy="370" rx="100" ry="80" fill="url(#redGrad)" stroke="#dc2626" stroke-width="1.5"/>

  <!-- Right Ventricle (bottom-right) -->
  <ellipse cx="510" cy="370" rx="100" ry="80" fill="url(#blueGrad)" stroke="#3b82f6" stroke-width="1.5"/>

  <!-- Aorta (top arch) -->
  <path d="M340,150 C340,60 460,60 460,150" fill="none" stroke="#dc2626" stroke-width="4" opacity="0.7"/>
  <ellipse cx="400" cy="85" rx="55" ry="30" fill="#fecaca" stroke="#dc2626" stroke-width="1.5" opacity="0.5"/>

  <!-- Pulmonary Artery -->
  <path d="M460,180 C500,120 560,100 600,140" fill="none" stroke="#3b82f6" stroke-width="3" opacity="0.6"/>

  <!-- Superior Vena Cava -->
  <path d="M540,150 L560,60" fill="none" stroke="#3b82f6" stroke-width="3" opacity="0.6"/>

  <!-- Valve indicators -->
  <ellipse cx="290" cy="290" rx="25" ry="8" fill="#fbbf24" stroke="#d97706" stroke-width="1" opacity="0.7"/>
  <ellipse cx="510" cy="290" rx="25" ry="8" fill="#fbbf24" stroke="#d97706" stroke-width="1" opacity="0.7"/>

  <!-- Title -->
  <text x="400" y="565" text-anchor="middle" font-family="system-ui" font-size="14" fill="#64748b" font-weight="600">Human Heart — Cross Section</text>
</svg>
`);

// ─── Drag Drop Fixture ───────────────────────────────────────────
const dragDropBlueprint: InteractiveDiagramBlueprint = {
  templateType: 'INTERACTIVE_DIAGRAM',
  title: 'Human Heart Anatomy',
  narrativeIntro: 'Label the major structures of the human heart by dragging each label to its correct position.',
  tasks: [],
  animationCues: { correctPlacement: '', incorrectPlacement: '' },
  diagram: {
    assetPrompt: 'Human heart cross-section anatomy diagram',
    assetUrl: HEART_DIAGRAM_SVG,
    width: 800,
    height: 600,
    zones: [
      { id: 'z_la', label: 'Left Atrium', x: 36.25, y: 35, radius: 8, shape: 'circle' as const, description: 'Receives oxygenated blood from the lungs via pulmonary veins', metadata: { category: 'Chambers' } },
      { id: 'z_ra', label: 'Right Atrium', x: 63.75, y: 35, radius: 8, shape: 'circle' as const, description: 'Receives deoxygenated blood from the body via vena cava', metadata: { category: 'Chambers' } },
      { id: 'z_lv', label: 'Left Ventricle', x: 36.25, y: 61.7, radius: 9, shape: 'circle' as const, description: 'Pumps oxygenated blood to the body via the aorta', metadata: { category: 'Chambers' } },
      { id: 'z_rv', label: 'Right Ventricle', x: 63.75, y: 61.7, radius: 9, shape: 'circle' as const, description: 'Pumps deoxygenated blood to the lungs via pulmonary arteries', metadata: { category: 'Chambers' } },
      { id: 'z_ao', label: 'Aorta', x: 50, y: 14.2, radius: 5, shape: 'circle' as const, description: 'Largest artery — carries oxygenated blood from the left ventricle to the body', metadata: { category: 'Vessels' } },
      { id: 'z_mv', label: 'Mitral Valve', x: 36.25, y: 48.3, radius: 3, shape: 'circle' as const, description: 'Controls blood flow from left atrium to left ventricle', metadata: { category: 'Valves' } },
      { id: 'z_tv', label: 'Tricuspid Valve', x: 63.75, y: 48.3, radius: 3, shape: 'circle' as const, description: 'Controls blood flow from right atrium to right ventricle', metadata: { category: 'Valves' } },
    ],
  },
  labels: [
    { id: 'l_la', text: 'Left Atrium', correctZoneId: 'z_la' },
    { id: 'l_ra', text: 'Right Atrium', correctZoneId: 'z_ra' },
    { id: 'l_lv', text: 'Left Ventricle', correctZoneId: 'z_lv' },
    { id: 'l_rv', text: 'Right Ventricle', correctZoneId: 'z_rv' },
    { id: 'l_ao', text: 'Aorta', correctZoneId: 'z_ao' },
    { id: 'l_mv', text: 'Mitral Valve', correctZoneId: 'z_mv' },
    { id: 'l_tv', text: 'Tricuspid Valve', correctZoneId: 'z_tv' },
  ],
  distractorLabels: [
    { id: 'd1', text: 'Pulmonary Vein', explanation: 'The pulmonary vein carries blood TO the heart, not a chamber of the heart.' },
    { id: 'd2', text: 'Coronary Sinus', explanation: 'The coronary sinus drains blood from the heart muscle itself.' },
  ],
  hints: [
    { zoneId: 'z_la', hintText: 'Upper-left chamber that receives blood from the lungs' },
    { zoneId: 'z_ra', hintText: 'Upper-right chamber that receives blood from the body' },
    { zoneId: 'z_ao', hintText: 'The large arched vessel at the top' },
  ],
  dragDropConfig: {
    interaction_mode: 'drag_drop',
    feedback_timing: 'immediate',
    label_style: 'text',
    placement_animation: 'spring',
    spring_stiffness: 300,
    spring_damping: 25,
    incorrect_animation: 'shake',
    show_placement_particles: true,
    leader_line_style: 'curved',
    leader_line_color: '#6366f1',
    leader_line_width: 2,
    leader_line_animate: true,
    pin_marker_shape: 'circle',
    tray_position: 'bottom',
    tray_layout: 'horizontal',
    tray_show_remaining: true,
    tray_show_categories: true,
    show_distractors: true,
    distractor_rejection_mode: 'immediate',
    zoom_enabled: false,
    max_attempts: 3,
    shuffle_labels: true,
  },
  interactionMode: 'drag_drop' as const,
};

// ─── Sequencing Fixture ──────────────────────────────────────────
const sequencingItems = [
  { id: 'seq1', content: 'Deoxygenated blood enters right atrium', description: 'From superior and inferior vena cava', icon: '🩸', orderIndex: 0 },
  { id: 'seq2', content: 'Blood flows to right ventricle', description: 'Through the tricuspid valve', icon: '⬇️', orderIndex: 1 },
  { id: 'seq3', content: 'Blood pumped to lungs', description: 'Via pulmonary arteries for gas exchange', icon: '🫁', orderIndex: 2 },
  { id: 'seq4', content: 'Oxygenated blood returns to left atrium', description: 'Via pulmonary veins', icon: '🔴', orderIndex: 3 },
  { id: 'seq5', content: 'Blood flows to left ventricle', description: 'Through the mitral (bicuspid) valve', icon: '⬇️', orderIndex: 4 },
  { id: 'seq6', content: 'Blood pumped to body', description: 'Via the aorta to systemic circulation', icon: '💪', orderIndex: 5 },
];

// ─── Sorting Fixture ─────────────────────────────────────────────
const sortingFixture = {
  items: [
    { id: 's1', content: 'Mitochondria', correctCategoryId: 'organelle', correctCategoryIds: ['organelle'], description: 'Powerhouse of the cell — ATP production', difficulty: 'easy' as const },
    { id: 's2', content: 'Ribosome', correctCategoryId: 'organelle', correctCategoryIds: ['organelle'], description: 'Protein synthesis from mRNA', difficulty: 'easy' as const },
    { id: 's3', content: 'Glucose', correctCategoryId: 'molecule', correctCategoryIds: ['molecule'], description: 'Simple sugar — primary energy source', difficulty: 'medium' as const },
    { id: 's4', content: 'DNA', correctCategoryId: 'molecule', correctCategoryIds: ['molecule'], description: 'Genetic material — double helix', difficulty: 'medium' as const },
    { id: 's5', content: 'Nucleus', correctCategoryId: 'organelle', correctCategoryIds: ['organelle'], description: 'Control center containing DNA', difficulty: 'easy' as const },
    { id: 's6', content: 'ATP', correctCategoryId: 'molecule', correctCategoryIds: ['molecule'], description: 'Energy currency of the cell', difficulty: 'hard' as const },
    { id: 's7', content: 'Golgi Apparatus', correctCategoryId: 'organelle', correctCategoryIds: ['organelle'], description: 'Packaging and shipping center', difficulty: 'medium' as const },
    { id: 's8', content: 'RNA', correctCategoryId: 'molecule', correctCategoryIds: ['molecule'], description: 'Messenger molecule for gene expression', difficulty: 'hard' as const },
  ],
  categories: [
    { id: 'organelle', label: 'Cell Organelles', description: 'Membrane-bound structures inside cells', color: '#6366f1' },
    { id: 'molecule', label: 'Biomolecules', description: 'Chemical compounds essential for life', color: '#ec4899' },
  ],
};

// ─── Memory Match Fixture ────────────────────────────────────────
const memoryPairs = [
  { id: 'mp1', front: 'Mitochondria', back: 'Powerhouse of the cell', frontType: 'text' as const, backType: 'text' as const, explanation: 'Mitochondria produce ATP through cellular respiration — the primary energy source for cells.' },
  { id: 'mp2', front: 'Nucleus', back: 'Control center', frontType: 'text' as const, backType: 'text' as const, explanation: 'The nucleus houses DNA and controls gene expression, directing all cell activities.' },
  { id: 'mp3', front: 'Ribosome', back: 'Protein factory', frontType: 'text' as const, backType: 'text' as const, explanation: 'Ribosomes translate messenger RNA into polypeptide chains — the building blocks of proteins.' },
  { id: 'mp4', front: 'Cell Membrane', back: 'Selective barrier', frontType: 'text' as const, backType: 'text' as const, explanation: 'The phospholipid bilayer selectively controls what molecules enter and exit the cell.' },
  { id: 'mp5', front: 'Chloroplast', back: 'Photosynthesis site', frontType: 'text' as const, backType: 'text' as const, explanation: 'Chloroplasts use light energy to convert CO2 and water into glucose and oxygen.' },
  { id: 'mp6', front: 'Endoplasmic Reticulum', back: 'Transport network', frontType: 'text' as const, backType: 'text' as const, explanation: 'The ER is a network of membranes that transports proteins (rough ER) and lipids (smooth ER).' },
];

// ─── Click to Identify Fixture ───────────────────────────────────
const identificationZones = [
  { id: 'iz_la', label: 'Left Atrium', x: 36.25, y: 35, radius: 8, shape: 'circle' as const },
  { id: 'iz_ra', label: 'Right Atrium', x: 63.75, y: 35, radius: 8, shape: 'circle' as const },
  { id: 'iz_lv', label: 'Left Ventricle', x: 36.25, y: 61.7, radius: 9, shape: 'circle' as const },
  { id: 'iz_rv', label: 'Right Ventricle', x: 63.75, y: 61.7, radius: 9, shape: 'circle' as const },
  { id: 'iz_ao', label: 'Aorta', x: 50, y: 14.2, radius: 5, shape: 'circle' as const },
  { id: 'iz_mv', label: 'Mitral Valve', x: 36.25, y: 48.3, radius: 3, shape: 'circle' as const },
];

const identificationPrompts = [
  { zoneId: 'iz_la', prompt: 'Click on the Left Atrium — the upper-left chamber', order: 0 },
  { zoneId: 'iz_ra', prompt: 'Click on the Right Atrium — the upper-right chamber', order: 1 },
  { zoneId: 'iz_lv', prompt: 'Click the chamber that pumps oxygenated blood to the body', order: 2 },
  { zoneId: 'iz_rv', prompt: 'Identify the chamber that pumps blood to the lungs', order: 3 },
  { zoneId: 'iz_ao', prompt: 'Click on the largest artery in the human body', order: 4 },
  { zoneId: 'iz_mv', prompt: 'Find the valve between the left atrium and left ventricle', order: 5 },
];

// ─── Trace Path Fixture ──────────────────────────────────────────
const tracePathZones = [
  { id: 'tp_ra', label: 'Right Atrium', x: 63.75, y: 35, radius: 5, shape: 'circle' as const },
  { id: 'tp_rv', label: 'Right Ventricle', x: 63.75, y: 61.7, radius: 5, shape: 'circle' as const },
  { id: 'tp_lungs', label: 'Lungs', x: 80, y: 20, radius: 5, shape: 'circle' as const },
  { id: 'tp_la', label: 'Left Atrium', x: 36.25, y: 35, radius: 5, shape: 'circle' as const },
  { id: 'tp_lv', label: 'Left Ventricle', x: 36.25, y: 61.7, radius: 5, shape: 'circle' as const },
  { id: 'tp_body', label: 'Body', x: 20, y: 80, radius: 5, shape: 'circle' as const },
];

const tracePaths = [
  {
    id: 'blood_flow',
    description: 'Trace the path of blood through the circulatory system',
    waypoints: [
      { zoneId: 'tp_ra', order: 0 },
      { zoneId: 'tp_rv', order: 1 },
      { zoneId: 'tp_lungs', order: 2 },
      { zoneId: 'tp_la', order: 3 },
      { zoneId: 'tp_lv', order: 4 },
      { zoneId: 'tp_body', order: 5 },
    ],
    requiresOrder: true,
  },
];

// ─── DragDrop Wrapper with DndContext + State ────────────────────
function DragDropTest({ blueprint }: { blueprint: InteractiveDiagramBlueprint }) {
  const [placedLabels, setPlacedLabels] = useState<PlacedLabel[]>([]);
  const [availableLabels, setAvailableLabels] = useState<Label[]>(() =>
    [...blueprint.labels].sort(() => Math.random() - 0.5)
  );
  const [draggingLabelId, setDraggingLabelId] = useState<string | null>(null);
  const [incorrectFeedback, setIncorrectFeedback] = useState<{ labelId: string; message: string } | null>(null);
  const [showHints, setShowHints] = useState(false);
  const [score, setScore] = useState(0);

  const mouseSensor = useSensor(MouseSensor, { activationConstraint: { distance: 5 } });
  const touchSensor = useSensor(TouchSensor, { activationConstraint: { delay: 200, tolerance: 5 } });
  const sensors = useSensors(mouseSensor, touchSensor);

  const handleDragStart = useCallback((event: DragStartEvent) => {
    setDraggingLabelId(event.active.id as string);
    setIncorrectFeedback(null);
  }, []);

  const handleDragEnd = useCallback((event: DragEndEvent) => {
    setDraggingLabelId(null);
    const { active, over } = event;
    if (!over) return;

    const labelId = active.id as string;
    const zoneId = over.id as string;
    const label = blueprint.labels.find(l => l.id === labelId);
    if (!label) return;

    const isCorrect = label.correctZoneId === zoneId;
    if (isCorrect) {
      setPlacedLabels(prev => [...prev, { labelId, zoneId, isCorrect: true }]);
      setAvailableLabels(prev => prev.filter(l => l.id !== labelId));
      setScore(prev => prev + 10);
    } else {
      setIncorrectFeedback({ labelId, message: `"${label.text}" doesn't belong there. Try again!` });
      setTimeout(() => setIncorrectFeedback(null), 2000);
    }
  }, [blueprint.labels]);

  const handleDragCancel = useCallback(() => {
    setDraggingLabelId(null);
  }, []);

  const handlePlace = useCallback((labelId: string, zoneId: string): boolean => {
    const label = blueprint.labels.find(l => l.id === labelId);
    if (!label) return false;
    const isCorrect = label.correctZoneId === zoneId;
    if (isCorrect) {
      setPlacedLabels(prev => [...prev, { labelId, zoneId, isCorrect: true }]);
      setAvailableLabels(prev => prev.filter(l => l.id !== labelId));
      setScore(prev => prev + 10);
    } else {
      setIncorrectFeedback({ labelId, message: `"${label.text}" doesn't belong there.` });
      setTimeout(() => setIncorrectFeedback(null), 2000);
    }
    return isCorrect;
  }, [blueprint.labels]);

  const isComplete = placedLabels.length === blueprint.labels.length;

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-4">
          <span className="text-sm font-medium text-gray-600 dark:text-gray-400">
            Score: {score} / {blueprint.labels.length * 10}
          </span>
          <span className="text-sm text-gray-500">
            {placedLabels.length}/{blueprint.labels.length} placed
          </span>
        </div>
        <button
          onClick={() => setShowHints(!showHints)}
          className="px-3 py-1 text-xs rounded bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300 hover:bg-amber-200"
        >
          {showHints ? 'Hide Hints' : 'Show Hints'}
        </button>
      </div>

      {isComplete && (
        <div className="mb-4 p-4 bg-green-50 dark:bg-green-900/30 border border-green-200 dark:border-green-800 rounded-lg text-center">
          <p className="text-green-700 dark:text-green-300 font-semibold">All structures labeled correctly!</p>
        </div>
      )}

      <DndContext
        sensors={sensors}
        collisionDetection={closestCenter}
        onDragStart={handleDragStart}
        onDragEnd={handleDragEnd}
        onDragCancel={handleDragCancel}
      >
        <EnhancedDragDropGame
          blueprint={blueprint}
          placedLabels={placedLabels}
          availableLabels={availableLabels}
          draggingLabelId={draggingLabelId}
          incorrectFeedback={incorrectFeedback}
          showHints={showHints}
          sensors={[]}
          onDragStart={handleDragStart}
          onDragEnd={handleDragEnd}
          onDragCancel={handleDragCancel}
          onPlace={handlePlace}
        />
      </DndContext>
    </div>
  );
}

// ─── Mechanic Tabs ───────────────────────────────────────────────
const MECHANICS: { key: string; label: string; icon: string }[] = [
  { key: 'drag_drop', label: 'Drag & Drop', icon: '🎯' },
  { key: 'sequencing', label: 'Sequencing', icon: '🔢' },
  { key: 'sorting', label: 'Sorting', icon: '📦' },
  { key: 'memory', label: 'Memory Match', icon: '🃏' },
  { key: 'click_identify', label: 'Click to Identify', icon: '👆' },
  { key: 'trace_path', label: 'Trace Path', icon: '🛤️' },
];

// ─── Click-to-Identify Test Wrapper (manages local progress) ─────
function ClickToIdentifyTest({
  onAction: parentAction,
}: {
  onAction: (action: MechanicAction) => ActionResult | null;
}) {
  const [progress, setProgress] = useState({
    currentPromptIndex: 0,
    completedZoneIds: [] as string[],
    incorrectAttempts: 0,
  });

  const handleAction = useCallback((action: MechanicAction): ActionResult | null => {
    const result = parentAction(action);
    if (action.type === 'identify') {
      const sorted = [...identificationPrompts].sort((a, b) => (a.order ?? 0) - (b.order ?? 0));
      const currentPrompt = sorted[progress.currentPromptIndex];
      if (currentPrompt?.zoneId === action.zoneId) {
        setProgress(prev => ({
          currentPromptIndex: prev.currentPromptIndex + 1,
          completedZoneIds: [...prev.completedZoneIds, action.zoneId],
          incorrectAttempts: prev.incorrectAttempts,
        }));
      } else {
        setProgress(prev => ({ ...prev, incorrectAttempts: prev.incorrectAttempts + 1 }));
      }
    }
    return result;
  }, [parentAction, progress.currentPromptIndex]);

  return (
    <EnhancedHotspotManager
      zones={identificationZones}
      prompts={identificationPrompts}
      config={{
        promptStyle: 'functional',
        selectionMode: 'sequential',
        highlightStyle: 'subtle',
        magnificationEnabled: false,
        showZoneCount: true,
      }}
      assetUrl={HEART_DIAGRAM_SVG}
      width={800}
      height={600}
      progress={progress}
      onAction={handleAction}
    />
  );
}

// ─── Trace Path Test Wrapper (manages local progress) ────────────
function TracePathTest({
  onAction: parentAction,
}: {
  onAction: (action: MechanicAction) => ActionResult | null;
}) {
  const [traceProgress, setTraceProgress] = useState({
    currentPathIndex: 0,
    pathProgressMap: Object.fromEntries(
      tracePaths.map(p => [p.id, { visitedWaypoints: [] as string[], isComplete: false }])
    ),
  });

  const handleAction = useCallback((action: MechanicAction): ActionResult | null => {
    const result = parentAction(action);
    if (action.type === 'visit_waypoint') {
      setTraceProgress(prev => {
        const existing = prev.pathProgressMap[action.pathId] || { visitedWaypoints: [], isComplete: false };
        const path = tracePaths.find(p => p.id === action.pathId);
        // Check correctness from config data
        const sorted = path ? [...path.waypoints].sort((a, b) => a.order - b.order) : [];
        const nextIdx = existing.visitedWaypoints.length;
        const isCorrectNext = path?.requiresOrder
          ? sorted[nextIdx]?.zoneId === action.zoneId
          : sorted.some(wp => wp.zoneId === action.zoneId && !existing.visitedWaypoints.includes(action.zoneId));
        if (!isCorrectNext) return prev;
        const newVisited = [...existing.visitedWaypoints, action.zoneId];
        const isComplete = newVisited.length >= sorted.length;
        return {
          ...prev,
          pathProgressMap: {
            ...prev.pathProgressMap,
            [action.pathId]: { visitedWaypoints: newVisited, isComplete },
          },
          currentPathIndex: isComplete && prev.currentPathIndex < tracePaths.length - 1
            ? prev.currentPathIndex + 1
            : prev.currentPathIndex,
        };
      });
    }
    return result;
  }, [parentAction]);

  return (
    <EnhancedPathDrawer
      zones={tracePathZones}
      paths={tracePaths}
      config={{
        particleTheme: 'droplets',
        particleSpeed: 'medium',
        showDirectionArrows: true,
        showWaypointLabels: true,
        showFullFlowOnComplete: true,
        pathType: 'linear',
        drawingMode: 'click_waypoints',
        instructions: 'Click on each structure in order to trace the path of blood flow through the circulatory system.',
      }}
      assetUrl={HEART_DIAGRAM_SVG}
      width={800}
      height={600}
      traceProgress={traceProgress}
      onAction={handleAction}
    />
  );
}

// ─── Shared Action Logger ─────────────────────────────────────────
function ActionLog({ actions }: { actions: MechanicAction[] }) {
  if (actions.length === 0) return null;
  const last = actions[actions.length - 1];
  return (
    <div className="mt-4 p-3 bg-gray-900 text-green-400 rounded-lg font-mono text-xs max-h-40 overflow-y-auto">
      <div className="text-gray-500 mb-1">Last action ({actions.length} total):</div>
      <pre>{JSON.stringify(last, null, 2)}</pre>
    </div>
  );
}

export default function TestMechanicsPage() {
  const [activeMechanic, setActiveMechanic] = useState('drag_drop');
  const [completedMechanics, setCompletedMechanics] = useState<Set<string>>(new Set());
  const [actionLog, setActionLog] = useState<MechanicAction[]>([]);

  const handleAction = useCallback((action: MechanicAction): ActionResult | null => {
    console.log('[V4 Action]', action);
    setActionLog(prev => [...prev.slice(-49), action]);
    return null;
  }, []);

  const handleComplete = (mechanic: string) => {
    setCompletedMechanics((prev) => new Set([...prev, mechanic]));
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      {/* Header */}
      <div className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 px-6 py-4">
        <h1 className="text-xl font-bold text-gray-900 dark:text-gray-100">
          V4 Mechanics Test — All 6 Priority Mechanics
        </h1>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
          Phase A verification: each mechanic with hardcoded fixture data
        </p>
      </div>

      {/* Mechanic tabs */}
      <div className="flex flex-wrap gap-2 px-6 py-4 bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
        {MECHANICS.map((m) => (
          <button
            key={m.key}
            onClick={() => setActiveMechanic(m.key)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
              activeMechanic === m.key
                ? 'bg-indigo-600 text-white shadow-md'
                : completedMechanics.has(m.key)
                ? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-200 border border-green-300'
                : 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300 hover:bg-gray-200'
            }`}
          >
            <span className="mr-1.5">{m.icon}</span>
            {m.label}
            {completedMechanics.has(m.key) && <span className="ml-1.5 text-green-600">✓</span>}
          </button>
        ))}
      </div>

      {/* Content area */}
      <div className="max-w-5xl mx-auto p-6">
        {activeMechanic === 'drag_drop' && (
          <div>
            <h2 className="text-lg font-semibold mb-2 text-gray-900 dark:text-gray-100">Drag & Drop — Human Heart Anatomy</h2>
            <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
              Features: leader lines, spring snap, particles, distractor labels, categories, hints
            </p>
            <DragDropTest blueprint={dragDropBlueprint} />
          </div>
        )}

        {activeMechanic === 'sequencing' && (
          <div>
            <h2 className="text-lg font-semibold mb-2 text-gray-900 dark:text-gray-100">Sequencing — Blood Flow Through the Heart</h2>
            <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
              Features: horizontal timeline, icon cards, connectors, endpoint labels
            </p>
            <EnhancedSequenceBuilder
              items={sequencingItems}
              correctOrder={['seq1', 'seq2', 'seq3', 'seq4', 'seq5', 'seq6']}
              config={{
                layout_mode: 'horizontal_timeline',
                card_type: 'icon_and_text',
                connector_style: 'arrow',
                show_position_numbers: true,
                show_endpoints: true,
                start_label: 'Deoxygenated',
                end_label: 'Oxygenated',
                instruction_text: 'Arrange the steps of blood flow through the heart in the correct order.',
              }}
              onAction={handleAction}
            />
            <ActionLog actions={actionLog.filter(a => a.mechanic === 'sequencing')} />
          </div>
        )}

        {activeMechanic === 'sorting' && (
          <div>
            <h2 className="text-lg font-semibold mb-2 text-gray-900 dark:text-gray-100">Sorting — Cell Biology Classification</h2>
            <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
              Features: bucket sort mode, difficulty levels, category colors
            </p>
            <EnhancedSortingCategories
              items={sortingFixture.items}
              categories={sortingFixture.categories}
              config={{
                items: sortingFixture.items,
                categories: sortingFixture.categories,
                sort_mode: 'bucket',
                item_card_type: 'text_only',
                instructions: 'Sort each item into the correct category: Cell Organelles or Biomolecules.',
              }}
              onAction={handleAction}
            />
            <ActionLog actions={actionLog.filter(a => a.mechanic === 'sorting_categories')} />
          </div>
        )}

        {activeMechanic === 'memory' && (
          <div>
            <h2 className="text-lg font-semibold mb-2 text-gray-900 dark:text-gray-100">Memory Match — Cell Structures & Functions</h2>
            <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
              Features: flip cards, explanation popups, attempts counter, checkmark on match
            </p>
            <EnhancedMemoryMatch
              config={{
                pairs: memoryPairs,
                gridSize: [4, 3],
                flipDurationMs: 400,
                showAttemptsCounter: true,
                instructions: 'Match each cell structure with its function by flipping cards.',
                card_back_style: 'gradient',
                matched_card_behavior: 'checkmark',
                show_explanation_on_match: true,
              }}
            />
          </div>
        )}

        {activeMechanic === 'click_identify' && (
          <div>
            <h2 className="text-lg font-semibold mb-2 text-gray-900 dark:text-gray-100">Click to Identify — Heart Structures</h2>
            <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
              Features: sequential prompts, functional descriptions, zone highlighting
            </p>
            <ClickToIdentifyTest onAction={handleAction} />
            <ActionLog actions={actionLog.filter(a => a.mechanic === 'click_to_identify')} />
          </div>
        )}

        {activeMechanic === 'trace_path' && (
          <div>
            <h2 className="text-lg font-semibold mb-2 text-gray-900 dark:text-gray-100">Trace Path — Blood Flow Circuit</h2>
            <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
              Features: click-waypoints mode, droplet particles, direction arrows, full flow animation
            </p>
            <TracePathTest onAction={handleAction} />
            <ActionLog actions={actionLog.filter(a => a.mechanic === 'trace_path')} />
          </div>
        )}
      </div>
    </div>
  );
}
