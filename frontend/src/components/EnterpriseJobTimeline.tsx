import { Clock } from 'lucide-react';
import StatusBadge from './StatusBadge';
import LoadingState from './LoadingState';
import EmptyState from './EmptyState';
import { formatDate } from '../utils/formatters';
import styles from './EnterpriseJobTimeline.module.css';

/**
 * components/EnterpriseJobTimeline.tsx
 *
 * Enterprise Job Timeline - a WIMLOGIC Enterprise Component (Phase 1A).
 *
 * Renders an ordered audit trail of events for a WACP Enterprise Job:
 * timestamp, status, and a human-readable summary for each entry. Like
 * EnterpriseJobProgress, this component carries no AI-CRE-specific
 * concepts - it accepts a generic list of timeline entries rather than the
 * AI-CRE WorkflowEvent shape directly, so any WACP-consuming application
 * (AI-ECOM, AI-HR, AI-ERP, AI-CRM, future products) can reuse it by mapping
 * its own execution/event records onto EnterpriseJobTimelineEntry.
 *
 * Composes existing Enterprise Components rather than reimplementing them
 * - StatusBadge for the per-event status pill, LoadingState for the
 * loading placeholder, and EmptyState for the no-activity-yet state - per
 * the "reuse before creating" rule in 02_ENTERPRISE_COMPONENTS.md.
 *
 * Entries are rendered in the order provided. Callers should supply them
 * sorted oldest-first so the timeline reads top-to-bottom as a life-cycle
 * narrative (Submitted -> Running -> ... -> Completed).
 */

export interface EnterpriseJobTimelineEntry {
  /** Unique key for the entry (e.g. the backend event_id). */
  id: string | number;
  /** Short category label for the event (e.g. "SUBMIT", "POLL", "CALLBACK"). Rendered as-is, never reinterpreted. */
  eventType: string;
  /** Verbatim backend status at the time of this event (e.g. "Pending", "Running", "Completed", "Failed", "Cancelled"). */
  status: string;
  /** Human-readable summary of what happened. */
  message: string;
  /** ISO timestamp (or any value accepted by `new Date()`) for when the event occurred. */
  timestamp: string;
}

export interface EnterpriseJobTimelineProps {
  entries: EnterpriseJobTimelineEntry[];
  isLoading?: boolean;
  emptyTitle?: string;
  emptyDescription?: string;
  id?: string;
}

export default function EnterpriseJobTimeline({
  entries,
  isLoading = false,
  emptyTitle = 'No Activity Yet',
  emptyDescription = 'Timeline events will appear here once this job is submitted.',
  id,
}: EnterpriseJobTimelineProps) {
  if (isLoading) {
    return (
      <LoadingState
        id={id ? `${id}-loading` : undefined}
        type="rows"
        rowsCount={3}
      />
    );
  }

  if (!entries || entries.length === 0) {
    return (
      <EmptyState
        id={id ? `${id}-empty` : undefined}
        icon={Clock}
        title={emptyTitle}
        description={emptyDescription}
      />
    );
  }

  return (
    <ol id={id || 'enterprise-job-timeline'} className={styles.timeline}>
      {entries.map((entry, index) => {
        const isLast = index === entries.length - 1;
        return (
          <li key={entry.id} className={styles.entry}>
            <div className={styles.markerColumn}>
              <span className={styles.marker} />
              {!isLast && <span className={styles.connector} />}
            </div>
            <div className={styles.content}>
              <div className={styles.entryHeader}>
                <span className={styles.eventType}>{entry.eventType}</span>
                <StatusBadge status={entry.status} type="workflow" />
              </div>
              <p className={styles.message}>{entry.message}</p>
              <span className={styles.timestamp}>{formatDate(entry.timestamp, true)}</span>
            </div>
          </li>
        );
      })}
    </ol>
  );
}
