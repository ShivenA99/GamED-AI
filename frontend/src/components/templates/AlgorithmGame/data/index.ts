import { StateTracerBlueprint } from '../types';
import { bubbleSortDemo } from './bubbleSortDemo';
import { binarySearchDemo } from './binarySearchDemo';
import { insertionSortDemo } from './insertionSortDemo';
import { bfsDemo } from './bfsDemo';
import { bstInsertDemo } from './bstInsertDemo';
import { fibonacciDPDemo } from './fibonacciDPDemo';
import { validParenthesesDemo } from './validParenthesesDemo';
import { reverseLinkedListDemo } from './reverseLinkedListDemo';

export {
  bubbleSortDemo,
  binarySearchDemo,
  insertionSortDemo,
  bfsDemo,
  bstInsertDemo,
  fibonacciDPDemo,
  validParenthesesDemo,
  reverseLinkedListDemo,
};

export interface DemoEntry {
  id: string;
  demo: StateTracerBlueprint;
}

export const allDemos: DemoEntry[] = [
  { id: 'bubble-sort', demo: bubbleSortDemo },
  { id: 'binary-search', demo: binarySearchDemo },
  { id: 'insertion-sort', demo: insertionSortDemo },
  { id: 'bfs', demo: bfsDemo },
  { id: 'bst-insert', demo: bstInsertDemo },
  { id: 'fibonacci-dp', demo: fibonacciDPDemo },
  { id: 'valid-parentheses', demo: validParenthesesDemo },
  { id: 'reverse-linked-list', demo: reverseLinkedListDemo },
];
