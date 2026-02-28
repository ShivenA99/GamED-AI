/**
 * caseNormalizer.ts — snake_case → camelCase helpers for blueprint data.
 *
 * The backend may send config keys in either snake_case or camelCase.
 * These helpers ensure a single canonical camelCase representation.
 */

/** snake_case → camelCase for a single key */
function snakeToCamelKey(key: string): string {
  return key.replace(/_([a-z])/g, (_, c) => c.toUpperCase());
}

/** Convert all snake_case keys in a flat object to camelCase. */
export function snakeToCamel<T extends Record<string, unknown>>(obj: T): Record<string, unknown> {
  const result: Record<string, unknown> = {};
  for (const [key, value] of Object.entries(obj)) {
    result[snakeToCamelKey(key)] = value;
  }
  return result;
}

/** Known snake_case → camelCase config field mappings for scenes */
const SCENE_CONFIG_MAP: Record<string, string> = {
  sequence_config: 'sequenceConfig',
  sorting_config: 'sortingConfig',
  memory_match_config: 'memoryMatchConfig',
  branching_config: 'branchingConfig',
  compare_config: 'compareConfig',
  click_to_identify_config: 'clickToIdentifyConfig',
  trace_path_config: 'tracePathConfig',
  drag_drop_config: 'dragDropConfig',
  description_matching_config: 'descriptionMatchingConfig',
  temporal_constraints: 'temporalConstraints',
  motion_paths: 'motionPaths',
  scoring_strategy: 'scoringStrategy',
  identification_prompts: 'identificationPrompts',
  distractor_labels: 'distractorLabels',
  interaction_mode: 'interactionMode',
  mode_transitions: 'modeTransitions',
  narrative_intro: 'narrativeIntro',
};

/**
 * Promote snake_case config keys to camelCase on a scene-like object.
 * Only copies the snake_case value if the camelCase key is not already present.
 */
export function normalizeSceneKeys<T extends Record<string, unknown>>(scene: T): T {
  const result = { ...scene };
  for (const [snakeKey, camelKey] of Object.entries(SCENE_CONFIG_MAP)) {
    if (result[snakeKey] !== undefined && result[camelKey] === undefined) {
      (result as Record<string, unknown>)[camelKey] = result[snakeKey];
    }
  }
  return result;
}

/**
 * Normalize inner keys of mechanic configs from snake_case to camelCase.
 *
 * The backend assembler sends snake_case inside config objects (e.g.,
 * sequenceConfig.correct_order, branchingConfig.start_node_id).
 * The frontend (store, components) expects camelCase.
 * This runs after Zod parse so all fields are present.
 */
export function normalizeMechanicConfigs(bp: Record<string, unknown>): void {
  // ─── sequenceConfig ─────────────────────────────────────
  const sc = bp.sequenceConfig as Record<string, unknown> | undefined;
  if (sc && typeof sc === 'object') {
    // correct_order → correctOrder
    if (sc.correct_order !== undefined && sc.correctOrder === undefined) {
      sc.correctOrder = sc.correct_order;
    }
    // sequence_type → sequenceType
    if (sc.sequence_type !== undefined && sc.sequenceType === undefined) {
      sc.sequenceType = sc.sequence_type;
    }
    // allow_partial_credit → allowPartialCredit
    if (sc.allow_partial_credit !== undefined && sc.allowPartialCredit === undefined) {
      sc.allowPartialCredit = sc.allow_partial_credit;
    }
    // instruction_text → instructionText
    if (sc.instruction_text !== undefined && sc.instructionText === undefined) {
      sc.instructionText = sc.instruction_text;
    }
    // Normalize items: content → text, explanation → description
    const items = sc.items;
    if (Array.isArray(items)) {
      for (const item of items) {
        if (typeof item === 'object' && item !== null) {
          const it = item as Record<string, unknown>;
          if (it.content !== undefined && it.text === undefined) {
            it.text = it.content;
          }
          if (it.explanation !== undefined && it.description === undefined) {
            it.description = it.explanation;
          }
          if (it.image_url !== undefined && it.image === undefined) {
            it.image = it.image_url;
          }
        }
      }
    }
  }

  // ─── branchingConfig ────────────────────────────────────
  const bc = bp.branchingConfig as Record<string, unknown> | undefined;
  if (bc && typeof bc === 'object') {
    if (bc.start_node_id !== undefined && bc.startNodeId === undefined) {
      bc.startNodeId = bc.start_node_id;
    }
    if (bc.show_path_taken !== undefined && bc.showPathTaken === undefined) {
      bc.showPathTaken = bc.show_path_taken;
    }
    if (bc.allow_backtrack !== undefined && bc.allowBacktrack === undefined) {
      bc.allowBacktrack = bc.allow_backtrack;
    }
    if (bc.show_consequences !== undefined && bc.showConsequences === undefined) {
      bc.showConsequences = bc.show_consequences;
    }
    if (bc.multiple_valid_endings !== undefined && bc.multipleValidEndings === undefined) {
      bc.multipleValidEndings = bc.multiple_valid_endings;
    }
  }

  // ─── sortingConfig ──────────────────────────────────────
  const stc = bp.sortingConfig as Record<string, unknown> | undefined;
  if (stc && typeof stc === 'object') {
    if (stc.allow_partial_credit !== undefined && stc.allowPartialCredit === undefined) {
      stc.allowPartialCredit = stc.allow_partial_credit;
    }
    if (stc.show_category_hints !== undefined && stc.showCategoryHints === undefined) {
      stc.showCategoryHints = stc.show_category_hints;
    }
    // Normalize items: correct_category_id → correctCategoryId
    const items = stc.items;
    if (Array.isArray(items)) {
      for (const item of items) {
        if (typeof item === 'object' && item !== null) {
          const it = item as Record<string, unknown>;
          if (it.correct_category_id !== undefined && it.correctCategoryId === undefined) {
            it.correctCategoryId = it.correct_category_id;
          }
        }
      }
    }
  }

  // ─── tracePathConfig ──────────────────────────────────
  const tpc = bp.tracePathConfig as Record<string, unknown> | undefined;
  if (tpc && typeof tpc === 'object') {
    if (tpc.path_type !== undefined && tpc.pathType === undefined) {
      tpc.pathType = tpc.path_type;
    }
    if (tpc.drawing_mode !== undefined && tpc.drawingMode === undefined) {
      tpc.drawingMode = tpc.drawing_mode;
    }
    if (tpc.particle_theme !== undefined && tpc.particleTheme === undefined) {
      tpc.particleTheme = tpc.particle_theme;
    }
    if (tpc.particle_speed !== undefined && tpc.particleSpeed === undefined) {
      tpc.particleSpeed = tpc.particle_speed;
    }
    if (tpc.color_transition_enabled !== undefined && tpc.colorTransitionEnabled === undefined) {
      tpc.colorTransitionEnabled = tpc.color_transition_enabled;
    }
    if (tpc.show_direction_arrows !== undefined && tpc.showDirectionArrows === undefined) {
      tpc.showDirectionArrows = tpc.show_direction_arrows;
    }
    if (tpc.show_waypoint_labels !== undefined && tpc.showWaypointLabels === undefined) {
      tpc.showWaypointLabels = tpc.show_waypoint_labels;
    }
    if (tpc.show_full_flow_on_complete !== undefined && tpc.showFullFlowOnComplete === undefined) {
      tpc.showFullFlowOnComplete = tpc.show_full_flow_on_complete;
    }
    if (tpc.submit_mode !== undefined && tpc.submitMode === undefined) {
      tpc.submitMode = tpc.submit_mode;
    }
  }

  // ─── memoryMatchConfig ──────────────────────────────────
  const mc = bp.memoryMatchConfig as Record<string, unknown> | undefined;
  if (mc && typeof mc === 'object') {
    if (mc.flip_duration_ms !== undefined && mc.flipDurationMs === undefined) {
      mc.flipDurationMs = mc.flip_duration_ms;
    }
    if (mc.show_attempts_counter !== undefined && mc.showAttemptsCounter === undefined) {
      mc.showAttemptsCounter = mc.show_attempts_counter;
    }
    if (mc.show_explanation_on_match !== undefined && mc.showExplanationOnMatch === undefined) {
      mc.showExplanationOnMatch = mc.show_explanation_on_match;
    }
  }
}

/**
 * Normalize misconceptions from backend dict format to frontend array format.
 *
 * Backend may send: { "chloroplast": "Plants have chloroplasts, not animals" }
 * Frontend expects: [{ trigger_label: "chloroplast", message: "Plants have..." }]
 */
export function normalizeMisconceptions(
  misconceptions: unknown,
): Array<{ trigger_label: string; message: string }> | undefined {
  if (misconceptions === undefined || misconceptions === null) {
    return undefined;
  }

  // Already an array — validate shape
  if (Array.isArray(misconceptions)) {
    return misconceptions.filter(
      (m): m is { trigger_label: string; message: string } =>
        typeof m === 'object' && m !== null && 'trigger_label' in m && 'message' in m,
    );
  }

  // Dict format from backend: { "label": "message" }
  if (typeof misconceptions === 'object') {
    return Object.entries(misconceptions as Record<string, string>).map(
      ([trigger_label, message]) => ({ trigger_label, message: String(message) }),
    );
  }

  return undefined;
}
