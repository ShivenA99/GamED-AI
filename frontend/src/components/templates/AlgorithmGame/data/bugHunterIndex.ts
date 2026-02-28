import { BugHunterBlueprint } from '../types';
import { bugHunterBinarySearch } from './bugHunterBinarySearch';
import { bugHunterBubbleSort } from './bugHunterBubbleSort';
import { bugHunterBFS } from './bugHunterBFS';
import { bugHunterFibonacci } from './bugHunterFibonacci';
import { bugHunterLinkedList } from './bugHunterLinkedList';
import { bugHunterStack } from './bugHunterStack';
import { bugHunterBST } from './bugHunterBST';
import { bugHunterInsertionSort } from './bugHunterInsertionSort';
import { bugHunterBinarySearchFreeText } from './bugHunterBinarySearchFreeText';
import { bugHunterRoundsDemo } from './bugHunterRoundsDemo';

export {
  bugHunterBinarySearch,
  bugHunterBubbleSort,
  bugHunterBFS,
  bugHunterFibonacci,
  bugHunterLinkedList,
  bugHunterStack,
  bugHunterBST,
  bugHunterInsertionSort,
  bugHunterBinarySearchFreeText,
  bugHunterRoundsDemo,
};

export interface BugHunterDemoEntry {
  id: string;
  demo: BugHunterBlueprint;
}

export const allBugHunterDemos: BugHunterDemoEntry[] = [
  { id: 'bh-binary-search', demo: bugHunterBinarySearch },
  { id: 'bh-bubble-sort', demo: bugHunterBubbleSort },
  { id: 'bh-bfs', demo: bugHunterBFS },
  { id: 'bh-fibonacci', demo: bugHunterFibonacci },
  { id: 'bh-linked-list', demo: bugHunterLinkedList },
  { id: 'bh-stack', demo: bugHunterStack },
  { id: 'bh-bst', demo: bugHunterBST },
  { id: 'bh-insertion-sort', demo: bugHunterInsertionSort },
  { id: 'bh-binary-search-free-text', demo: bugHunterBinarySearchFreeText },
  { id: 'bh-rounds-gauntlet', demo: bugHunterRoundsDemo },
];
