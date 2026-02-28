/**
 * engine/schemas/ — Blueprint validation boundary (Layer 4).
 *
 * Public API: parseBlueprint() is the single entry point.
 */

export { parseBlueprint, isMultiSceneParseResult } from './parseBlueprint';
export type { ParseResult, MultiSceneParseResult } from './parseBlueprint';
export { BlueprintSchema } from './blueprintSchema';
export { MultiSceneBlueprintSchema } from './gameSequenceSchema';
export { normalizeSceneKeys, normalizeMisconceptions, snakeToCamel } from './caseNormalizer';
