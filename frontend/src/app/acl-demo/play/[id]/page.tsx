import { Suspense } from 'react';
import PlayClient from './PlayClient';

const GAME_IDS = [
  'bio-k12-plant-cell-drag-drop',
  'bio-k12-mitosis-sequencing',
  'bio-k12-food-chains-sorting',
  'bio-undergrad-organelles-click-identify',
  'bio-undergrad-cardiovascular-trace-path',
  'bio-undergrad-dna-enzymes-description',
  'bio-undergrad-inheritance-memory',
  'bio-grad-clinical-diagnosis-branching',
  'bio-grad-evolution-mechanisms-compare',
  'bio-grad-cellular-respiration-trace-path',
  'hist-k12-american-revolution-sequencing',
  'hist-k12-historical-figures-memory',
  'hist-k12-roman-empire-trace-path',
  'hist-undergrad-wwi-causes-sorting',
  'hist-undergrad-revolutions-compare',
  'hist-undergrad-industrial-revolution-drag-drop',
  'hist-undergrad-ancient-civilizations-click-identify',
  'hist-grad-historiographic-description',
  'hist-grad-versailles-branching',
  'hist-grad-cold-war-sequencing',
  'cs-k12-computer-parts-drag-drop',
  'cs-k12-network-data-trace-path',
  'cs-k12-bubble-sort-state-tracer',
  'cs-undergrad-uml-click-identify',
  'cs-undergrad-algorithm-complexity-sorting',
  'cs-undergrad-binary-search-bug-hunter',
  'cs-undergrad-bfs-algorithm-builder',
  'cs-grad-tcp-udp-compare',
  'cs-grad-dp-complexity-analyzer',
  'cs-grad-scheduling-constraint-puzzle',
  'math-k12-geometry-drag-drop',
  'math-k12-linear-equation-sequencing',
  'math-k12-number-types-sorting',
  'math-undergrad-calculus-description-matching',
  'math-undergrad-matrix-ops-memory',
  'math-undergrad-function-types-click-identify',
  'math-undergrad-integration-trace-path',
  'math-grad-proof-strategy-branching',
  'math-grad-numerical-methods-compare',
  'math-grad-vector-spaces-drag-drop',
  'ling-k12-sentence-parts-drag-drop',
  'ling-k12-word-types-sorting',
  'ling-k12-sentence-building-sequencing',
  'ling-undergrad-phonology-trace-path',
  'ling-undergrad-morphemes-click-identify',
  'ling-undergrad-language-families-memory',
  'ling-undergrad-semantic-roles-description',
  'ling-grad-syntax-trees-compare',
  'ling-grad-language-acquisition-branching',
  'ling-grad-phonological-processes-sorting',
];

export function generateStaticParams() {
  return GAME_IDS.map((id) => ({ id }));
}

export default async function ACLDemoPlayPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return (
    <Suspense fallback={<div className="animate-pulse p-8"><div className="h-64 bg-gray-200 rounded" /></div>}>
      <PlayClient id={id} />
    </Suspense>
  );
}
