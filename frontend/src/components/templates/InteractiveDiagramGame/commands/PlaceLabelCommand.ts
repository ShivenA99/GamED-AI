/**
 * PlaceLabelCommand - Command for placing a label on a zone
 *
 * Implements the Command Pattern for undoable label placement.
 * Captures the state needed to reverse the action.
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
 * PlaceLabelCommand - Represents placing a label on a zone.
 *
 * On execute: Places the label on the zone
 * On undo: Removes the label from the zone (returns it to available labels)
 */
export class PlaceLabelCommand implements GameCommand {
  readonly id: string;
  readonly description: string;
  readonly timestamp: number;
  readonly type: GameCommandType = 'place_label';

  private wasSuccessful: boolean = false;
  private previousZoneId: string | null = null;

  constructor(
    private readonly store: LabelStoreActions,
    private readonly labelId: string,
    private readonly zoneId: string,
    private readonly labelText: string
  ) {
    this.id = generateId();
    this.timestamp = Date.now();
    this.description = `Place "${labelText}" on zone`;

    // Check if label was already placed somewhere (for undo)
    const placedLabels = store.getPlacedLabels();
    const existing = placedLabels.find((p) => p.labelId === labelId);
    if (existing) {
      this.previousZoneId = existing.zoneId;
    }
  }

  execute(): void {
    this.wasSuccessful = this.store.placeLabel(this.labelId, this.zoneId);
  }

  undo(): void {
    if (this.wasSuccessful) {
      // Remove the label from the zone
      this.store.removeLabel(this.labelId);

      // If label was previously on a different zone, restore it there
      if (this.previousZoneId) {
        this.store.placeLabel(this.labelId, this.previousZoneId);
      }
    }
  }

  canExecute(): boolean {
    // Check if label is available
    const availableLabels = this.store.getAvailableLabels();
    const placedLabels = this.store.getPlacedLabels();

    const isAvailable = availableLabels.some((l) => l.id === this.labelId);
    const isPlaced = placedLabels.some((p) => p.labelId === this.labelId);

    return isAvailable || isPlaced;
  }

  canUndo(): boolean {
    // Can undo if the label was successfully placed
    return this.wasSuccessful;
  }

  /**
   * Get the result of the placement for analytics
   */
  wasPlacementSuccessful(): boolean {
    return this.wasSuccessful;
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
      zoneId: this.zoneId,
      labelText: this.labelText,
      wasSuccessful: this.wasSuccessful,
      previousZoneId: this.previousZoneId,
    };
  }
}

/**
 * Factory function for creating PlaceLabelCommand
 * Makes it easier to use with the command history
 */
export function createPlaceLabelCommand(
  store: LabelStoreActions,
  labelId: string,
  zoneId: string,
  labelText: string
): PlaceLabelCommand {
  return new PlaceLabelCommand(store, labelId, zoneId, labelText);
}
