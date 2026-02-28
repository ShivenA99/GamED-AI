import { ComplexityAnalyzerBlueprint } from '../types';
import { complexityAnalyzerBinarySearch } from './complexityAnalyzerBinarySearch';
import { complexityAnalyzerBubbleSort } from './complexityAnalyzerBubbleSort';
import { complexityAnalyzerBFS } from './complexityAnalyzerBFS';
import { complexityAnalyzerFibonacci } from './complexityAnalyzerFibonacci';
import { complexityAnalyzerLinkedList } from './complexityAnalyzerLinkedList';
import { complexityAnalyzerStack } from './complexityAnalyzerStack';
import { complexityAnalyzerBST } from './complexityAnalyzerBST';
import { complexityAnalyzerInsertionSort } from './complexityAnalyzerInsertionSort';

export {
  complexityAnalyzerBinarySearch,
  complexityAnalyzerBubbleSort,
  complexityAnalyzerBFS,
  complexityAnalyzerFibonacci,
  complexityAnalyzerLinkedList,
  complexityAnalyzerStack,
  complexityAnalyzerBST,
  complexityAnalyzerInsertionSort,
};

export interface ComplexityAnalyzerDemoEntry {
  id: string;
  demo: ComplexityAnalyzerBlueprint;
}

export const allComplexityAnalyzerDemos: ComplexityAnalyzerDemoEntry[] = [
  { id: 'ca-binary-search', demo: complexityAnalyzerBinarySearch },
  { id: 'ca-bubble-sort', demo: complexityAnalyzerBubbleSort },
  { id: 'ca-bfs', demo: complexityAnalyzerBFS },
  { id: 'ca-fibonacci', demo: complexityAnalyzerFibonacci },
  { id: 'ca-linked-list', demo: complexityAnalyzerLinkedList },
  { id: 'ca-stack', demo: complexityAnalyzerStack },
  { id: 'ca-bst', demo: complexityAnalyzerBST },
  { id: 'ca-insertion-sort', demo: complexityAnalyzerInsertionSort },
];
