'use client';

import {
  BoardRendererProps,
} from './constraintPuzzleTypes';
import { BOARD_REGISTRY, normalizeBoardType } from './boardRegistry';

/**
 * O(1) dispatch to the correct board component based on boardType.
 * Normalizes LLM-generated board type variants before lookup.
 */
export default function BoardRouter(props: BoardRendererProps) {
  const canonicalType = normalizeBoardType(props.config.boardType);
  const entry = BOARD_REGISTRY[canonicalType];

  if (!entry) {
    return (
      <div className="p-4 text-red-500 text-sm">
        Unknown board type: &quot;{props.config.boardType}&quot; (normalized: &quot;{canonicalType}&quot;)
      </div>
    );
  }

  const BoardComponent = entry.component;
  return <BoardComponent {...props} />;
}
