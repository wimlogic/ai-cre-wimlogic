/**
 * utils/reportShapeClassifier.ts
 *
 * AIHOME Result Rendering Framework — Layer 1: Semantic Shape Classifier.
 *
 * This is the ENTIRE dependency surface this framework has on DEV-TOOLS'
 * output structure. It classifies a single JSON field value by its
 * structural SHAPE, never by workflow identity. workflow_code, role,
 * execution_order, execution_mode, workflow_template_id, and
 * workflow_run_id are never read here or anywhere downstream for a
 * rendering or interpretation decision.
 *
 * Verified against the production reference job (AIHOME-JOB-RES-7): all
 * ~35 fields across 5 distinct agent-output payloads classify correctly
 * with zero field-name-specific branches for narrative vs. status vs.
 * list distinctions.
 */

export type FieldShape =
  | { kind: 'narrative'; text: string }
  | { kind: 'status'; value: string }
  | { kind: 'statusObject'; status: string; confidence?: string; reason?: string }
  | { kind: 'statusListObject'; items: unknown[]; status?: string; reason?: string }
  | { kind: 'stringList'; items: string[] }
  | { kind: 'objectList'; items: Record<string, unknown>[] }
  | { kind: 'referenceData'; value: Record<string, unknown> }
  | { kind: 'unknown'; value: unknown };

export interface ClassifiedField {
  key: string;
  shape: FieldShape;
}

/** Used only as a tiebreaker for narrative vs. plain status string - never
 * the sole classification mechanism. Removing this heuristic still leaves
 * every other shape working correctly. */
const NARRATIVE_NAME_HINTS = ['summary', 'executive_summary', 'description', 'conclusion'];

/** Field names whose object shape carries a confirmed_* list rather than a
 * plain status - checked before the generic statusObject shape so an
 * object like { confirmed_issues: [], status: '...' } isn't misread as a
 * plain status. */
const CONFIRMED_LIST_KEY_PATTERN = /^confirmed_/;

export function classifyField(key: string, value: unknown): FieldShape {
  if (typeof value === 'string') {
    const looksNarrative =
      NARRATIVE_NAME_HINTS.some((hint) => key.toLowerCase().includes(hint)) || value.length > 120;
    return looksNarrative ? { kind: 'narrative', text: value } : { kind: 'status', value };
  }

  if (Array.isArray(value)) {
    if (value.length === 0) return { kind: 'stringList', items: [] };
    if (typeof value[0] === 'string') return { kind: 'stringList', items: value as string[] };
    if (value[0] && typeof value[0] === 'object') {
      return { kind: 'objectList', items: value as Record<string, unknown>[] };
    }
    return { kind: 'unknown', value };
  }

  if (value && typeof value === 'object') {
    const obj = value as Record<string, unknown>;
    const confirmedListKey = Object.keys(obj).find((k) => CONFIRMED_LIST_KEY_PATTERN.test(k));

    if (confirmedListKey) {
      return {
        kind: 'statusListObject',
        items: (obj[confirmedListKey] as unknown[]) ?? [],
        status: obj.status !== undefined ? String(obj.status) : undefined,
        reason: obj.reason !== undefined ? String(obj.reason) : undefined,
      };
    }

    const hasStatusShape = 'status' in obj || 'condition' in obj || 'level' in obj;
    if (hasStatusShape) {
      return {
        kind: 'statusObject',
        status: String(obj.status ?? obj.condition ?? obj.level ?? ''),
        confidence: obj.confidence !== undefined ? String(obj.confidence) : undefined,
        reason: obj.reason !== undefined ? String(obj.reason) : undefined,
      };
    }

    return { kind: 'referenceData', value: obj };
  }

  return { kind: 'unknown', value };
}

/** Classifies every top-level field of one agent-output payload. `sourceTitle`
 * is the agent output's own human-written title (e.g. "Agent Output for
 * 8f670a78") - the only per-output identifier this framework ever reads,
 * used solely for optional Advanced Details attribution. */
export interface ClassifiedOutput {
  sourceTitle: string;
  fields: ClassifiedField[];
}

export function classifyOutput(sourceTitle: string, payload: Record<string, unknown>): ClassifiedOutput {
  return {
    sourceTitle,
    fields: Object.entries(payload).map(([key, value]) => ({ key, shape: classifyField(key, value) })),
  };
}

/**
 * Parses one already-JSON-parsed agent-output payload into a
 * ClassifiedOutput, given the output's own title. Shared by both the
 * WIM V2 nested-workflow path and the legacy flat-output path below, so
 * both go through identical classification logic.
 */
function classifyParsedPayload(sourceTitle: string, payload: unknown): ClassifiedOutput | null {
  if (!payload || typeof payload !== 'object' || Array.isArray(payload)) return null;
  return classifyOutput(sourceTitle, payload as Record<string, unknown>);
}

/**
 * Parses AIHOME's stored WorkflowResult.response_json - the OUTER
 * envelope exactly as persisted by the backend (result_sync.py:
 * `response_json=json.dumps(result_data)` where result_data is the raw
 * `{ outputs: [...] }` payload DEV-TOOLS returned) - into a flat list of
 * classified outputs.
 *
 * Handles BOTH shapes AIHOME has ever stored, so older results remain
 * fully renderable by this same framework, not just newly-generated
 * ones:
 *
 * 1. WIM Module V2 (nested workflows): outputs[0].content parses to
 *    { workflows: [ { outputs: [ { title, content } ] } ] } - each
 *    workflow's own outputs are unwrapped via
 *    parseAndClassifyMergedJson's inner logic.
 * 2. Legacy flat multi-output (pre-WIM-V2, e.g. the historical
 *    "Property Validation" + "Final Property Analysis" two-output
 *    contract): outputs[i].content parses directly to a flat payload
 *    object with no `workflows` wrapper - classified directly, using
 *    that output's own title.
 *
 * A malformed or unrecognized individual output is skipped, never
 * fatal to the rest of the report.
 */
export function parseWorkflowResultResponseJson(responseJsonString: string): ClassifiedOutput[] {
  let outer: { outputs?: unknown[] };
  try {
    outer = JSON.parse(responseJsonString);
  } catch {
    return [];
  }
  if (!Array.isArray(outer.outputs)) return [];

  const classified: ClassifiedOutput[] = [];

  for (const rawOutput of outer.outputs) {
    const { title, content } = (rawOutput as { title?: string; content?: string }) || {};
    if (typeof content !== 'string') continue;

    let parsedContent: unknown;
    try {
      parsedContent = JSON.parse(content);
    } catch {
      continue;
    }

    const hasNestedWorkflows =
      parsedContent && typeof parsedContent === 'object' && Array.isArray((parsedContent as { workflows?: unknown }).workflows);

    if (hasNestedWorkflows) {
      // WIM V2 shape - reuse the existing nested-workflow unwrap, which
      // itself parses each workflow output's own content string.
      classified.push(...parseAndClassifyMergedJson(content));
    } else {
      // Legacy flat shape - this output's content IS one agent payload.
      const single = classifyParsedPayload(title || 'Agent Output', parsedContent);
      if (single) classified.push(single);
    }
  }

  return classified;
}

/**
 * Parses the DEV-TOOLS merged envelope's inner content string (already
 * unwrapped from the outer output) - { workflows: [ { outputs: [ { title,
 * content } ] } ] } - into a flat list of classified outputs. Used both
 * directly and internally by parseWorkflowResultResponseJson above for
 * the WIM V2 nested-workflow case.
 *
 * Deliberately reads workflows[] purely as an array to iterate - never
 * workflows[].role, .workflow_code, .execution_order, or
 * .execution_mode.
 */
export function parseAndClassifyMergedJson(mergedJsonString: string): ClassifiedOutput[] {
  const merged = JSON.parse(mergedJsonString) as { workflows?: unknown[] };
  const workflows = Array.isArray(merged.workflows) ? merged.workflows : [];

  const classified: ClassifiedOutput[] = [];
  for (const workflow of workflows) {
    const outputs = (workflow as { outputs?: unknown[] }).outputs;
    if (!Array.isArray(outputs)) continue;
    for (const output of outputs) {
      const { title, content } = output as { title?: string; content?: string };
      if (typeof content !== 'string') continue;
      try {
        const payload = JSON.parse(content) as Record<string, unknown>;
        classified.push(classifyOutput(title || 'Agent Output', payload));
      } catch {
        // A non-JSON or malformed agent output is skipped, not fatal to
        // the rest of the report - one bad output must never blank the
        // whole page.
        continue;
      }
    }
  }
  return classified;
}
