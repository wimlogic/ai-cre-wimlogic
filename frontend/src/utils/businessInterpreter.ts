/**
 * utils/businessInterpreter.ts
 *
 * AIHOME Result Rendering Framework — Layer 2: Business Interpreter.
 *
 * Takes the Semantic Classifier's per-output field bags (still knowing
 * which output each field came from) and produces ONE interpreted report:
 * one Executive Summary, one ranked Key Risks list, one merged
 * Recommendations list, one merged Priority Actions list - organized by
 * business topic, never by originating workflow.
 *
 * Per-item source attribution is retained internally (each output's own
 * human-written `title`, e.g. "Agent Output for 8f670a78") but is used
 * ONLY for the optional, collapsed-by-default Advanced Details view - the
 * normal report never shows which agent produced which item.
 *
 * Nothing in this file reads workflow_code, role, execution_order,
 * execution_mode, workflow_template_id, or workflow_run_id - the
 * classifier layer never surfaces them, and this layer has no reason to
 * ask for them back.
 */

import { ClassifiedOutput } from './reportShapeClassifier';

export type Tone = 'success' | 'warning' | 'error' | 'neutral';

export interface PropertyFact {
  label: string;
  value: string;
}

export interface RankedFinding {
  title: string;
  severity: string | null; // normalized label: 'High' | 'Medium' | 'Low' | null
  tone: Tone;
  detail?: string;
  evidence?: string[];
  sourceOutputTitles: string[];
}

export interface ConditionTopic {
  label: string;
  status: string;
  tone: Tone;
  confidence?: string;
  reason?: string;
  sourceOutputTitles: string[];
}

export interface AttributedText {
  text: string;
  sourceOutputTitles: string[];
}

export interface SourceAttribution {
  outputTitle: string;
  fieldKeys: string[];
}

export interface InterpretedReport {
  executiveSummary: string;
  overallStatus: { label: string; tone: Tone };
  propertyFacts: PropertyFact[];
  conditionSummary: ConditionTopic[];
  keyRisks: RankedFinding[];
  recommendations: AttributedText[];
  priorityActions: AttributedText[];
  nextSteps: string[];
  attribution: SourceAttribution[];
}

// ---------------------------------------------------------------------------
// Text normalization + similarity-based deduplication
// ---------------------------------------------------------------------------

function normalizeText(s: string): string {
  return s.toLowerCase().replace(/[.,;:!?'"()]/g, '').replace(/\s+/g, ' ').trim();
}

function tokenSet(s: string): Set<string> {
  return new Set(normalizeText(s).split(' ').filter((t) => t.length > 2));
}

/** Jaccard token overlap. Two strings describing the same underlying issue
 * in different words (e.g. two agents both flagging the address conflict)
 * typically share 40%+ of their meaningful tokens even with very different
 * phrasing; unrelated strings typically share under 15%. */
function similarity(a: string, b: string): number {
  const ta = tokenSet(a);
  const tb = tokenSet(b);
  if (ta.size === 0 || tb.size === 0) return 0;
  let overlap = 0;
  for (const t of ta) if (tb.has(t)) overlap++;
  return overlap / Math.min(ta.size, tb.size);
}

const SIMILARITY_MERGE_THRESHOLD = 0.5;

/** Merges near-duplicate strings, keeping the longest (most detailed)
 * phrasing per cluster and combining source attribution from every
 * duplicate folded into it. */
function dedupeAttributedStrings(
  items: { text: string; sourceOutputTitle: string }[]
): AttributedText[] {
  const clusters: { text: string; sourceOutputTitles: Set<string> }[] = [];

  for (const item of items) {
    const existing = clusters.find((c) => similarity(c.text, item.text) >= SIMILARITY_MERGE_THRESHOLD);
    if (existing) {
      existing.sourceOutputTitles.add(item.sourceOutputTitle);
      if (item.text.length > existing.text.length) existing.text = item.text;
    } else {
      clusters.push({ text: item.text, sourceOutputTitles: new Set([item.sourceOutputTitle]) });
    }
  }

  return clusters.map((c) => ({ text: c.text, sourceOutputTitles: Array.from(c.sourceOutputTitles) }));
}

// ---------------------------------------------------------------------------
// Severity / confidence / status normalization
// ---------------------------------------------------------------------------

const SEVERITY_RANK: Record<string, number> = { high: 0, critical: 0, medium: 1, low: 2 };

function severityRank(value: string | null | undefined): number {
  if (!value) return 3;
  return SEVERITY_RANK[value.toLowerCase()] ?? 3;
}

/** Severity and confidence use the SAME word ("Low", "High") for opposite
 * meanings on different axes - a Low-risk finding and a Low-confidence
 * finding must never render with the same tone. This function is only
 * ever used for severity/risk-level values; confidence values are
 * normalized separately and always render as neutral/grey. */
function severityTone(value: string | null | undefined): Tone {
  const rank = severityRank(value);
  if (rank === 0) return 'error';
  if (rank === 1) return 'warning';
  if (rank === 2) return 'success';
  return 'neutral';
}

function statusTone(value: string): Tone {
  const v = value.toLowerCase();
  if (['completed', 'active', 'sound', 'confirmed', 'good'].some((w) => v.includes(w))) return 'success';
  if (['at risk', 'issues_found', 'incomplete', 'warning', 'pending'].some((w) => v.includes(w))) return 'warning';
  if (['undetermined', 'unresolved', 'error', 'failed', 'critical'].some((w) => v.includes(w))) return 'error';
  return 'neutral';
}

// ---------------------------------------------------------------------------
// Field-name -> business-topic heuristics
// ---------------------------------------------------------------------------
// These are pattern-based heuristics over FIELD NAMES that recur across
// arbitrary future agent outputs (e.g. any future workflow's
// "recommendations" or "priority_actions" field matches the same
// pattern) - never a lookup keyed by workflow identity. A field with a
// name this framework has never seen still classifies correctly via
// classifyField's shape rules; these patterns only decide WHICH business
// bucket a stringList/objectList lands in.

const ACTION_KEY_PATTERN = /action|priority_repair|immediate_attention|follow.?up|inspection_scope/i;
const RECOMMENDATION_KEY_PATTERN = /recommend/i;

function humanizeLabel(key: string): string {
  return key
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

/**
 * An objectList item only qualifies as a risk finding if it carries an
 * EXPLICIT severity signal (severity / risk_level). This is deliberately
 * strict: a bare data-validation object shaped like { code, message,
 * details } (no severity field) is NOT promoted to a "Key Risk" here,
 * even though it clearly describes a problem.
 *
 * Two reasons, both confirmed against the production reference job:
 * 1. A loose `'code' in item || 'title' in item` check (an earlier
 *    version of this function) incorrectly captured plain reference data
 *    - e.g. submitted-image objects shaped like { url, image_type,
 *    notes } - as fake "risk findings" with no real severity.
 * 2. Where a workflow DOES synthesize business risk from underlying
 *    validation issues (as this job's risk-assessment output does,
 *    turning "ADDRESS_CONFLICT" into a properly severity-tagged "Subject
 *    property identity is unresolved" risk finding), that synthesis is
 *    exactly the kind of interpretation DEV-TOOLS' specialist agents
 *    already perform. Re-promoting the raw, severity-less validation
 *    error alongside it would have AIHOME re-deriving a risk judgment a
 *    specialist agent already made - duplicative business logic this
 *    framework should not invent on its own.
 *
 * A raw validation error/warning with no risk-assessment counterpart
 * (e.g. a future single-workflow job with no separate risk agent) is
 * still fully visible - just via Advanced Details / the JSON download
 * rather than as a top-level Key Risk, until it carries its own severity
 * signal.
 */
function looksLikeRiskFinding(item: Record<string, unknown>): boolean {
  return 'severity' in item || 'risk_level' in item;
}

function extractFindingTitle(item: Record<string, unknown>): string {
  return String(item.title ?? item.item ?? item.issue ?? item.message ?? item.code ?? 'Finding');
}

function extractFindingSeverity(item: Record<string, unknown>): string | null {
  const raw = item.risk_level ?? item.severity;
  return raw !== undefined && raw !== null ? String(raw) : null;
}

function extractFindingDetail(item: Record<string, unknown>): string | undefined {
  const raw = item.reason ?? item.why_high ?? item.description ?? item.message;
  return raw !== undefined ? String(raw) : undefined;
}

function extractFindingEvidence(item: Record<string, unknown>): string[] | undefined {
  const raw = item.evidence;
  return Array.isArray(raw) ? raw.map(String) : undefined;
}

// ---------------------------------------------------------------------------
// Main interpretation
// ---------------------------------------------------------------------------

export function interpretReport(classifiedOutputs: ClassifiedOutput[]): InterpretedReport {
  const narratives: { text: string; sourceOutputTitle: string; key: string }[] = [];
  const propertyFacts: PropertyFact[] = [];
  const conditionTopicsRaw: (ConditionTopic & { key: string })[] = [];
  const riskFindingsRaw: (RankedFinding & { key: string })[] = [];
  const recommendationsRaw: { text: string; sourceOutputTitle: string }[] = [];
  const actionsRaw: { text: string; sourceOutputTitle: string }[] = [];
  const attribution: SourceAttribution[] = [];

  for (const output of classifiedOutputs) {
    const fieldKeysTouched: string[] = [];

    for (const { key, shape } of output.fields) {
      fieldKeysTouched.push(key);
      switch (shape.kind) {
        case 'narrative':
          narratives.push({ text: shape.text, sourceOutputTitle: output.sourceTitle, key });
          break;

        case 'referenceData':
          for (const [subKey, subValue] of Object.entries(shape.value)) {
            if (typeof subValue === 'string' || typeof subValue === 'number' || typeof subValue === 'boolean') {
              propertyFacts.push({ label: humanizeLabel(subKey), value: String(subValue) });
            }
          }
          break;

        case 'statusObject':
          conditionTopicsRaw.push({
            key,
            label: humanizeLabel(key),
            status: shape.status,
            tone: statusTone(shape.status),
            confidence: shape.confidence,
            reason: shape.reason,
            sourceOutputTitles: [output.sourceTitle],
          });
          break;

        case 'statusListObject':
          conditionTopicsRaw.push({
            key,
            label: humanizeLabel(key),
            status: shape.status ?? (shape.items.length > 0 ? 'Issues found' : 'No issues confirmed'),
            tone: shape.items.length > 0 ? 'warning' : 'neutral',
            reason: shape.reason,
            sourceOutputTitles: [output.sourceTitle],
          });
          // Any confirmed items inside a statusListObject are themselves
          // findings-shaped - fold them into risk findings if they carry
          // enough structure, otherwise they're already represented by
          // the topic's own status/reason above.
          for (const rawItem of shape.items) {
            if (rawItem && typeof rawItem === 'object' && looksLikeRiskFinding(rawItem as Record<string, unknown>)) {
              const item = rawItem as Record<string, unknown>;
              riskFindingsRaw.push({
                key,
                title: extractFindingTitle(item),
                severity: extractFindingSeverity(item),
                tone: severityTone(extractFindingSeverity(item)),
                detail: extractFindingDetail(item),
                evidence: extractFindingEvidence(item),
                sourceOutputTitles: [output.sourceTitle],
              });
            }
          }
          break;

        case 'objectList':
          for (const rawItem of shape.items) {
            if (looksLikeRiskFinding(rawItem)) {
              riskFindingsRaw.push({
                key,
                title: extractFindingTitle(rawItem),
                severity: extractFindingSeverity(rawItem),
                tone: severityTone(extractFindingSeverity(rawItem)),
                detail: extractFindingDetail(rawItem),
                evidence: extractFindingEvidence(rawItem),
                sourceOutputTitles: [output.sourceTitle],
              });
            }
          }
          break;

        case 'stringList':
          if (ACTION_KEY_PATTERN.test(key)) {
            for (const item of shape.items) actionsRaw.push({ text: item, sourceOutputTitle: output.sourceTitle });
          } else if (RECOMMENDATION_KEY_PATTERN.test(key)) {
            for (const item of shape.items) recommendationsRaw.push({ text: item, sourceOutputTitle: output.sourceTitle });
          }
          // Other stringLists (e.g. missing_fields) are reference-data-
          // adjacent and intentionally not surfaced as risks or actions
          // in the main topics - they remain available via Advanced
          // Details through the attribution/raw-output path.
          break;

        case 'status':
        case 'unknown':
          // Deliberately not surfaced in the main report topics - a bare
          // status string with no narrative/finding shape doesn't map to
          // any business topic on its own, and an `unknown` shape by
          // definition isn't safe to interpret. Both remain visible in
          // Advanced Details / the raw JSON download.
          break;
      }
    }

    attribution.push({ outputTitle: output.sourceTitle, fieldKeys: fieldKeysTouched });
  }

  // --- Executive summary: exactly one, preferring report-ready naming ---
  const preferredNarrative =
    narratives.find((n) => /executive_summary|conclusion/i.test(n.key)) ??
    narratives.slice().sort((a, b) => b.text.length - a.text.length)[0];
  const executiveSummary = preferredNarrative?.text ?? 'No executive summary was provided for this analysis.';

  // Any other narrative becomes a condition-topic-style supporting note
  // rather than being silently discarded.
  for (const n of narratives) {
    if (n !== preferredNarrative) {
      conditionTopicsRaw.push({
        key: n.key,
        label: humanizeLabel(n.key),
        status: n.text,
        tone: 'neutral',
        sourceOutputTitles: [n.sourceOutputTitle],
      });
    }
  }

  // --- Overall status: derived from the highest-severity risk found, or
  // the most severe-toned condition topic if no risks exist ---
  const worstRisk = riskFindingsRaw.slice().sort((a, b) => severityRank(a.severity) - severityRank(b.severity))[0];
  const overallStatus = worstRisk
    ? { label: `${worstRisk.severity ?? 'Needs Review'} Priority Items Found`, tone: worstRisk.tone }
    : { label: 'No Elevated Risks Found', tone: 'success' as Tone };

  // --- Merge condition topics by normalized label (business topic, not
  // source) - two outputs both describing "safety issues" collapse into
  // one topic entry rather than appearing twice ---
  const conditionByLabel = new Map<string, ConditionTopic>();
  for (const topic of conditionTopicsRaw) {
    const existing = conditionByLabel.get(topic.label);
    if (!existing) {
      conditionByLabel.set(topic.label, topic);
    } else {
      existing.sourceOutputTitles = Array.from(new Set([...existing.sourceOutputTitles, ...topic.sourceOutputTitles]));
    }
  }

  // --- Deduplicate + rank risk findings ---
  const riskClusters: RankedFinding[] = [];
  for (const finding of riskFindingsRaw) {
    const existing = riskClusters.find((c) => similarity(c.title, finding.title) >= SIMILARITY_MERGE_THRESHOLD);
    if (existing) {
      existing.sourceOutputTitles = Array.from(new Set([...existing.sourceOutputTitles, ...finding.sourceOutputTitles]));
      if (severityRank(finding.severity) < severityRank(existing.severity)) {
        existing.severity = finding.severity;
        existing.tone = finding.tone;
      }
    } else {
      riskClusters.push({ ...finding });
    }
  }
  riskClusters.sort((a, b) => severityRank(a.severity) - severityRank(b.severity));

  const recommendations = dedupeAttributedStrings(recommendationsRaw);
  const priorityActions = dedupeAttributedStrings(actionsRaw);

  const nextSteps = priorityActions.slice(0, 5).map((a) => a.text);

  return {
    executiveSummary,
    overallStatus,
    propertyFacts,
    conditionSummary: Array.from(conditionByLabel.values()),
    keyRisks: riskClusters,
    recommendations,
    priorityActions,
    nextSteps,
    attribution,
  };
}

export { severityTone, statusTone };
