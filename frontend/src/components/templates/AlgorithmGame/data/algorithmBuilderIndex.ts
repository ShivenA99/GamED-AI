import { AlgorithmBuilderBlueprint } from '../types';
import { algorithmBuilderBinarySearch } from './algorithmBuilderBinarySearch';
import { algorithmBuilderBubbleSort } from './algorithmBuilderBubbleSort';
import { algorithmBuilderBFS } from './algorithmBuilderBFS';
import { algorithmBuilderFibonacci } from './algorithmBuilderFibonacci';
import { algorithmBuilderLinkedList } from './algorithmBuilderLinkedList';
import { algorithmBuilderStack } from './algorithmBuilderStack';
import { algorithmBuilderBST } from './algorithmBuilderBST';
import { algorithmBuilderInsertionSort } from './algorithmBuilderInsertionSort';

export {
  algorithmBuilderBinarySearch,
  algorithmBuilderBubbleSort,
  algorithmBuilderBFS,
  algorithmBuilderFibonacci,
  algorithmBuilderLinkedList,
  algorithmBuilderStack,
  algorithmBuilderBST,
  algorithmBuilderInsertionSort,
};

export interface AlgorithmBuilderDemoEntry {
  id: string;
  demo: AlgorithmBuilderBlueprint;
}

export const allAlgorithmBuilderDemos: AlgorithmBuilderDemoEntry[] = [
  { id: 'ab-binary-search', demo: algorithmBuilderBinarySearch },
  { id: 'ab-bubble-sort', demo: algorithmBuilderBubbleSort },
  { id: 'ab-bfs', demo: algorithmBuilderBFS },
  { id: 'ab-fibonacci', demo: algorithmBuilderFibonacci },
  { id: 'ab-linked-list', demo: algorithmBuilderLinkedList },
  { id: 'ab-stack', demo: algorithmBuilderStack },
  { id: 'ab-bst', demo: algorithmBuilderBST },
  { id: 'ab-insertion-sort', demo: algorithmBuilderInsertionSort },
];
