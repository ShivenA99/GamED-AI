import type { InteractiveDiagramBlueprint } from '../types';
import { dragDropDemo } from './dragDropDemo';
import { clickToIdentifyDemo } from './clickToIdentifyDemo';
import { tracePathDemo } from './tracePathDemo';
import { sequencingDemo } from './sequencingDemo';
import { sortingDemo } from './sortingDemo';
import { memoryMatchDemo } from './memoryMatchDemo';
import { branchingDemo } from './branchingDemo';
import { compareContrastDemo } from './compareContrastDemo';
import { descriptionMatchingDemo } from './descriptionMatchingDemo';

export interface DiagramDemoEntry {
  id: string;
  name: string;
  description: string;
  icon: string;
  mechanic: string;
  color: string;
  borderColor: string;
  blueprint: InteractiveDiagramBlueprint;
}

export const allDiagramDemos: DiagramDemoEntry[] = [
  { id: 'drag-drop', name: 'Human Heart', description: 'Drag labels onto the parts of a human heart', icon: '🎯', mechanic: 'drag_drop', color: 'from-blue-500/20 to-blue-600/10', borderColor: 'border-blue-500/30 hover:border-blue-400', blueprint: dragDropDemo },
  { id: 'click-to-identify', name: 'Flower Anatomy', description: 'Identify flower parts when given their function', icon: '👆', mechanic: 'click_to_identify', color: 'from-teal-500/20 to-teal-600/10', borderColor: 'border-teal-500/30 hover:border-teal-400', blueprint: clickToIdentifyDemo },
  { id: 'trace-path', name: 'Digestive System', description: 'Trace the path of food through the digestive tract', icon: '✏️', mechanic: 'trace_path', color: 'from-red-500/20 to-red-600/10', borderColor: 'border-red-500/30 hover:border-red-400', blueprint: tracePathDemo },
  { id: 'sequencing', name: 'Blood Flow Steps', description: 'Put the steps of cardiac blood flow in order', icon: '🔢', mechanic: 'sequencing', color: 'from-purple-500/20 to-purple-600/10', borderColor: 'border-purple-500/30 hover:border-purple-400', blueprint: sequencingDemo },
  { id: 'sorting', name: 'Cell Features', description: 'Sort features into plant cell or animal cell categories', icon: '📂', mechanic: 'sorting_categories', color: 'from-green-500/20 to-green-600/10', borderColor: 'border-green-500/30 hover:border-green-400', blueprint: sortingDemo },
  { id: 'memory-match', name: 'Organ Functions', description: 'Match each organ to its primary function', icon: '🃏', mechanic: 'memory_match', color: 'from-amber-500/20 to-amber-600/10', borderColor: 'border-amber-500/30 hover:border-amber-400', blueprint: memoryMatchDemo },
  { id: 'branching', name: 'Chest Pain Diagnosis', description: 'Make diagnostic decisions for a patient with chest pain', icon: '🌳', mechanic: 'branching_scenario', color: 'from-rose-500/20 to-rose-600/10', borderColor: 'border-rose-500/30 hover:border-rose-400', blueprint: branchingDemo },
  { id: 'compare-contrast', name: 'Plant vs Animal Cell', description: 'Compare structures between plant and animal cells', icon: '⚖️', mechanic: 'compare_contrast', color: 'from-orange-500/20 to-orange-600/10', borderColor: 'border-orange-500/30 hover:border-orange-400', blueprint: compareContrastDemo },
  { id: 'description-matching', name: 'Flower Parts', description: 'Match each part of a flower to its description', icon: '🔗', mechanic: 'description_matching', color: 'from-indigo-500/20 to-indigo-600/10', borderColor: 'border-indigo-500/30 hover:border-indigo-400', blueprint: descriptionMatchingDemo },
];

export {
  dragDropDemo,
  clickToIdentifyDemo,
  tracePathDemo,
  sequencingDemo,
  sortingDemo,
  memoryMatchDemo,
  branchingDemo,
  compareContrastDemo,
  descriptionMatchingDemo,
};
