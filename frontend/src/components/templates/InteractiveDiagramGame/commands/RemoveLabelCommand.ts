/**
 * RemoveLabelCommand - Command for removing a label from a zone
 *
 * Implements the Command Pattern for undoable label removal.
 * Captures the zone the label was on for restoration.
 */

import { GameCommand, GameCommandType } from './types';

/**
 * Store actions interface - matches useInteractiveDiagramState
 */
export interface LabelStoreActions {
  placeLabel: (labelId: string, zoneId: string) => boolean;
  removeLabel: (labelId: string) => void;
  getPlacedLabels: () => Array<{ labelId: string; zoneId: string; isCorrect: boolean }>;
  getAvailableLabels: () => Array<{ id: string; text: string }>;
}

/**
 * Generates a unique command ID
 */
function generateId(): string {
  return `cmd_${Date.now()}_${Math.random().toString(36).substring(2, 11)}`;
}

/**
 * RemoveLabelCommand - Represents removing a label from a zone.
 *
 * On execute: Removes the label from the zone (returns to available)
 * On undo: Places the label back on the zone it was removed from
 */
export class RemoveLabelCommand implements GameCommand {
  readonly id: string;
  readonly description: string;
  readonly timestamp: number;
  readonly type: GameCommandType = 'remove_label';

  private wasExecuted: boolean = false;
  private removedFromZoneId: string | null = null;
  private wasCorrect: boolean = false;

  constructor(
    private readonly store: LabelStoreActions,
    private readonly labelId: string,
    private readonly labelText: string
  ) {
    this.id = generateId();
    this.timestamp = Date.now();
    this.description = `Remove "${labelText}" from zone`;

    // Capture current state for undo
    const placedLabels = store.getPlacedLabels();
    const placed = placedLabels.find((p) => p.labelId === labelId);
    if (placed) {
      this.removedFromZoneId = placed.zoneId;
      this.wasCorrect = placed.isCorrect;
    }
  }

  execute(): void {
    if (this.removedFromZoneId) {
      this.store.removeLabel(this.labelId);
      this.wasExecuted = true;
    }
  }

  undo(): void {
    if (this.wasExecuted && this.removedFromZoneId) {
      // Place the label back where it was
      this.store.placeLabel(this.labelId, this.removedFromZoneId);
    }
  }

  canExecute(): boolean {
    // Can only remove if label is currently placed
    const placedLabels = this.store.getPlacedLabels();
    return placedLabels.some((p) => p.labelId === this.labelId);
  }

  canUndo(): boolean {
    // Can undo if we have a zone to restore to
    return this.wasExecuted && this.removedFromZoneId !== null;
  }

  /**
   * Check if the removed label was correctly placed
   */
  wasCorrectlyPlaced(): boolean {
    return this.wasCorrect;
  }

  /**
   * Get the zone ID the label was removed from
   */
  getRemovedFromZone(): string | null {
    return this.removedFromZoneId;
  }

  /**
   * Get command data for serialization
   */
  toJSON(): Record<string, unknown> {
    return {
      id: this.id,
      type: this.type,
      timestamp: this.timestamp,
      labelId: this.labelId,
      labelText: this.labelText,
      removedFromZoneId: this.removedFromZoneId,
      wasCorrect: this.wasCorrect,
    };
  }
}

/**
 * Factory function for creating RemoveLabelCommand
 */
export function createRemoveLabelCommand(
  store: LabelStoreActions,
  labelId: string,
  labelText: string
): RemoveLabelCommand {
  return new RemoveLabelCommand(store, labelId, labelText);
}
