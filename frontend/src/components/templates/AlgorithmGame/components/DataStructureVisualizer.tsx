'use client';

import {
  DataStructure,
  ArrayDataStructure,
  GraphDataStructure,
  TreeDataStructure,
  DPTableDataStructure,
  StackDataStructure,
  QueueDataStructure,
  LinkedListDataStructure,
  HeapDataStructure,
  HashMapDataStructure,
  CustomObjectDataStructure,
} from '../types';
import ArrayVisualizer from './visualizers/ArrayVisualizer';
import GraphVisualizer from './visualizers/GraphVisualizer';
import TreeVisualizer from './visualizers/TreeVisualizer';
import DPTableVisualizer from './visualizers/DPTableVisualizer';
import StackVisualizer from './visualizers/StackVisualizer';
import QueueVisualizer from './visualizers/QueueVisualizer';
import LinkedListVisualizer from './visualizers/LinkedListVisualizer';
import HeapVisualizer from './visualizers/HeapVisualizer';
import HashMapVisualizer from './visualizers/HashMapVisualizer';
import CustomObjectVisualizer from './visualizers/CustomObjectVisualizer';

interface DataStructureVisualizerProps {
  dataStructure: DataStructure;
  theme?: 'dark' | 'light';
}

// Normalize LLM-generated type names to canonical types.
function normalizeType(type: string): string {
  const t = type.toLowerCase().replace(/[-\s]+/g, '_');

  // Detect compound/list types — LLM sometimes emits Python-style lists as the type
  if (t.includes('[') || t.includes(',') || t.includes("'")) return 'compound';

  if (t.includes('array') || t.includes('sorted_array')) return 'array';
  if (t.includes('graph')) return 'graph';
  if (t.includes('tree')) return 'tree';
  if (t.includes('dp_table') || t.includes('matrix') || t.includes('table')) return 'dp_table';
  if (t.includes('stack')) return 'stack';
  if (t.includes('queue') || t.includes('deque') || t.includes('fifo') || t.includes('bfs_queue')) return 'queue';
  if (t.includes('linked_list') || t === 'linkedlist') return 'linked_list';
  if (t.includes('heap') || t.includes('priority_queue')) return 'heap';
  if (t.includes('hash') || t.includes('map') || t.includes('dict')) return 'hash_map';
  return t;
}

// For compound types, extract sub-data-structures from the object's keys.
// Each sub-key (e.g. "priority_queue", "distances_map") is itself a DS object.
function extractSubStructures(ds: Record<string, any>): { key: string; subDS: DataStructure }[] {
  const metaKeys = new Set(['type', 'highlights', 'label']);
  const subs: { key: string; subDS: DataStructure }[] = [];

  for (const [key, value] of Object.entries(ds)) {
    if (metaKeys.has(key) || typeof value !== 'object' || value === null) continue;

    // Infer the sub-structure's type from its key name
    const inferredType = normalizeType(key);
    const subDS = { ...value, type: value.type || inferredType } as DataStructure;
    subs.push({ key, subDS });
  }

  return subs;
}

function renderSingle(dataStructure: DataStructure, theme: 'dark' | 'light') {
  const dsType = normalizeType(dataStructure.type);
  switch (dsType) {
    case 'array':
      return <ArrayVisualizer dataStructure={dataStructure as ArrayDataStructure} theme={theme} />;
    case 'graph':
      return <GraphVisualizer dataStructure={dataStructure as GraphDataStructure} theme={theme} />;
    case 'tree':
      return <TreeVisualizer dataStructure={dataStructure as TreeDataStructure} theme={theme} />;
    case 'dp_table':
      return <DPTableVisualizer dataStructure={dataStructure as DPTableDataStructure} theme={theme} />;
    case 'stack':
      return <StackVisualizer dataStructure={dataStructure as StackDataStructure} theme={theme} />;
    case 'queue':
      return <QueueVisualizer dataStructure={dataStructure as QueueDataStructure} theme={theme} />;
    case 'linked_list':
      return <LinkedListVisualizer dataStructure={dataStructure as LinkedListDataStructure} theme={theme} />;
    case 'heap':
      return <HeapVisualizer dataStructure={dataStructure as HeapDataStructure} theme={theme} />;
    case 'hash_map':
      return <HashMapVisualizer dataStructure={dataStructure as HashMapDataStructure} theme={theme} />;
    case 'custom':
    default:
      return <CustomObjectVisualizer dataStructure={dataStructure as CustomObjectDataStructure} theme={theme} />;
  }
}

export default function DataStructureVisualizer({
  dataStructure,
  theme = 'dark',
}: DataStructureVisualizerProps) {
  const dsType = normalizeType(dataStructure.type);

  // Compound types: render each sub-structure with its own visualizer
  if (dsType === 'compound') {
    const subs = extractSubStructures(dataStructure as unknown as Record<string, any>);
    if (subs.length > 0) {
      return (
        <div className="space-y-3">
          {subs.map(({ key, subDS }) => (
            <div key={key}>
              {renderSingle(subDS, theme)}
            </div>
          ))}
        </div>
      );
    }
    // Fallback if no sub-structures found
    return <CustomObjectVisualizer dataStructure={dataStructure as CustomObjectDataStructure} theme={theme} />;
  }

  return renderSingle(dataStructure, theme);
}
