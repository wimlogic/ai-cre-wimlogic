import { CrePropertyAnalysisReport } from '../types';
import EmptyState from './EmptyState';
import { FileText, ChevronRight } from 'lucide-react';
import styles from './PropertyReportHistory.module.css';

/**
 * components/PropertyReportHistory.tsx
 *
 * Phase 2A. ONLY successfully-synchronized report records - sourced
 * from GET /property-analysis-reports/?property_id=X. This is
 * deliberately a completely separate component and data source from
 * PropertyExecutionHistory: a Failed, Cancelled, or sync-failed
 * execution never produces a PropertyAnalysisReport row (confirmed
 * directly against result_sync.py), so this list can never contain
 * anything but genuine, readable reports. Every row exposes exactly
 * one action: Open Report.
 */

export interface PropertyReportHistoryProps {
  reports: CrePropertyAnalysisReport[];
  isLoading: boolean;
  onOpenReport: (report: CrePropertyAnalysisReport) => void;
}

export default function PropertyReportHistory({ reports, isLoading, onOpenReport }: PropertyReportHistoryProps) {
  if (isLoading) {
    return <div className={styles.loading}>Loading reports...</div>;
  }

  if (reports.length === 0) {
    return (
      <EmptyState
        icon={FileText}
        title="No Reports Yet"
        description="Completed analysis reports for this property will appear here."
      />
    );
  }

  return (
    <div className={styles.list} id="property-report-history">
      {reports.map((report) => (
        <button
          key={report.id}
          type="button"
          className={styles.row}
          onClick={() => onOpenReport(report)}
        >
          <FileText className={styles.icon} />
          <div className={styles.rowMain}>
            <span className={styles.date}>
              {new Date(report.created_at).toLocaleDateString(undefined, {
                month: 'short', day: 'numeric', year: 'numeric',
              })}
            </span>
            {report.recommendation && (
              <span className={styles.excerpt}>{report.recommendation}</span>
            )}
          </div>
          <span className={styles.openLabel}>
            Open Report
            <ChevronRight className={styles.chevron} />
          </span>
        </button>
      ))}
    </div>
  );
}
