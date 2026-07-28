import ExpandableSection from './ExpandableSection';
import { AlertCircle } from 'lucide-react';
import styles from './BusinessIntentCheckboxes.module.css';

/**
 * components/BusinessIntentCheckboxes.tsx
 *
 * Shared by every submission surface that lets a user choose which
 * Business Intents to request in a job (WACP 1.1's business_intent +
 * additional_business_intents) - currently PropertyRunAnalysisPanel
 * (Properties > Reports > Run New Analysis) and AIOrchestration (the
 * standalone "AI Orchestration" page's Configure Analysis form).
 *
 * PROPERTY_ANALYSIS is checked by default (the parent component's
 * initial state should include it), but is a REGULAR, fully togglable
 * checkbox like the other seven - it is a sensible default, not a
 * restriction. The parent is responsible for computing which selected
 * intent becomes the primary business_intent (the first, in the fixed
 * order below) and which become additional_business_intents (the rest)
 * when submitting - see either parent's handleRunAnalysis /
 * handleGenerateAnalysis for that logic.
 *
 * At least one intent must be selected before a job can be submitted;
 * this component only renders the inline warning when none are checked
 * - the parent is responsible for actually disabling its own submit
 * button based on the same `selected.size === 0` condition.
 */

export const ALL_BUSINESS_INTENTS = [
  'PROPERTY_ANALYSIS',
  'IMAGE_DESIGN',
  'RENOVATION_PLANNER',
  'DAMAGE_DETECTION',
  'ROOM_CLASSIFICATION',
  'ROI_ANALYSIS',
  'MATERIAL_SELECTION',
  'WORK_ORDER_GENERATION',
] as const;

function humanizeIntentLabel(intent: string): string {
  return intent.replace(/_/g, ' ').toLowerCase().replace(/\b\w/g, (c) => c.toUpperCase());
}

export interface BusinessIntentCheckboxesProps {
  selected: Set<string>;
  onToggle: (intent: string) => void;
  disabled?: boolean;
  defaultExpanded?: boolean;
}

export default function BusinessIntentCheckboxes({
  selected, onToggle, disabled = false, defaultExpanded = true,
}: BusinessIntentCheckboxesProps) {
  return (
    <ExpandableSection title="Business Intents" defaultExpanded={defaultExpanded}>
      <div className={styles.intentCheckboxList}>
        {ALL_BUSINESS_INTENTS.map((intent) => (
          <label key={intent} className={styles.intentCheckboxRow}>
            <input
              type="checkbox"
              checked={selected.has(intent)}
              onChange={() => onToggle(intent)}
              disabled={disabled}
            />
            <span>{humanizeIntentLabel(intent)}</span>
          </label>
        ))}
      </div>
      {selected.size === 0 ? (
        <p className={styles.intentWarningText}>
          <AlertCircle className={styles.intentWarningIcon} />
          Select at least one Business Intent to run an analysis.
        </p>
      ) : (
        <p className={styles.intentHelpText}>
          Selected analyses run together in the same job, in the order shown above.
        </p>
      )}
    </ExpandableSection>
  );
}
