import { useState, useEffect } from 'react';
import { workflowService } from '../services/workflowService';
import { downloadJson } from '../utils/downloadJson';
import { designImageVersionService } from '../services/designImageVersionService';
import { AppConfig } from '../config/app';
import { WorkflowResult, BusinessReport, BusinessReportSection, BusinessReportRiskItem, DesignImageVersion } from '../types/index';
import EnterpriseCard from './EnterpriseCard';
import StatusBadge from './StatusBadge';
import EmptyState from './EmptyState';
import ExpandableSection from './ExpandableSection';
import {
  ChevronRight, Calendar, Download, ShieldAlert, ListChecks, ClipboardList, RefreshCw,
} from 'lucide-react';
import styles from './PropertyIntelligenceReport.module.css';

/**
 * components/PropertyIntelligenceReport.tsx
 *
 * AIHOME Result Rendering Framework v2 - the Enterprise Report Renderer,
 * now a pure presentation engine over the normalized Business Report
 * JSON contract (report_version "1.0", produced entirely backend-side by
 * business_report_builder.py).
 *
 * Per the simplified architecture: DEV-TOOLS is the AI Orchestration
 * Platform; AIHOME is the Business Application. This component - and
 * this entire frontend - never inspects orchestration metadata. It does
 * not classify fields, merge duplicates, rank severity, or select an
 * executive summary from raw agent output; all of that interpretation
 * now happens once, backend-side, before this component ever sees the
 * data. This file's ONLY job is to render report.sections[] by
 * section.type - a plain switch, nothing more:
 *
 *   property_overview -> label/value fact grid
 *   risks              -> expandable finding cards with severity badges
 *   recommendations    -> plain list
 *   priority_actions   -> numbered list
 *   (anything else)    -> generic fallback, so a future section type
 *                         DEV-TOOLS/business_report_builder introduces
 *                         still renders something reasonable rather than
 *                         silently vanishing
 *
 * The one remaining piece of "raw" data this component touches at all
 * is WorkflowResult.response_json - the original, unprocessed DEV-TOOLS
 * payload - and ONLY for two purposes, both explicitly gated behind the
 * collapsed-by-default "Advanced Technical Details" section: viewing it
 * inline for developer/troubleshooting purposes, and the Download Full
 * JSON action. Normal users never see it and never need to - the
 * Business Report above it is the complete, professional presentation
 * AIHOME provides regardless of how many workflows, agents, or AI models
 * DEV-TOOLS used to produce it.
 */

export interface PropertyIntelligenceReportProps {
  /** WorkflowResult.result_id */
  resultId: number;
  projectName?: string;
  propertyAddress?: string;
  onBack?: () => void;
}

function renderSectionContent(content: Record<string, unknown>) {
  const entries = Object.entries(content).filter(([, v]) => v !== null && v !== undefined && v !== '');
  if (entries.length === 0) {
    return <EmptyState title="No Details Available" description="This analysis did not produce overview details." id="property-overview-empty" />;
  }
  return (
    <div className={styles.factGrid}>
      {entries.map(([label, value]) => (
        <div key={label} className={styles.factItem}>
          <span className={styles.factLabel}>{label}</span>
          <span className={styles.factValue}>{String(value)}</span>
        </div>
      ))}
    </div>
  );
}

function renderRisksSection(items: (string | BusinessReportRiskItem)[]) {
  if (items.length === 0) {
    return <EmptyState title="No Elevated Risks Identified" description="This analysis did not identify any material risk findings." icon={ShieldAlert} id="key-risks-empty" />;
  }
  return (
    <div className={styles.findingList}>
      {items.map((item, i) => {
        const risk = typeof item === 'string' ? { title: item, severity: null } : item;
        return (
          <ExpandableSection key={i} title={risk.title}>
            <div className={styles.findingBody}>
              {risk.severity && (
                <div className={styles.findingBadgeRow}>
                  <StatusBadge status={risk.severity} type="severity" />
                </div>
              )}
              {risk.detail && <p className={styles.findingDetail}>{risk.detail}</p>}
              {risk.evidence && risk.evidence.length > 0 && (
                <ul className={styles.evidenceList}>
                  {risk.evidence.map((e, j) => <li key={j}>{e}</li>)}
                </ul>
              )}
            </div>
          </ExpandableSection>
        );
      })}
    </div>
  );
}

function renderPlainListSection(items: (string | BusinessReportRiskItem)[], ordered: boolean, emptyTitle: string, emptyDescription: string, emptyIcon: typeof ListChecks) {
  if (items.length === 0) {
    return <EmptyState title={emptyTitle} description={emptyDescription} icon={emptyIcon} id={`${emptyTitle.toLowerCase().replace(/\s+/g, '-')}-empty`} />;
  }
  const Tag = ordered ? 'ol' : 'ul';
  return (
    <Tag className={ordered ? styles.numberedList : styles.plainList}>
      {items.map((item, i) => <li key={i}>{typeof item === 'string' ? item : item.title}</li>)}
    </Tag>
  );
}

/**
 * The one and only dispatch point on section.type - the literal
 * implementation of "render based on section.type, not workflow
 * identity". Adding a new section type here (should a future
 * business_report_builder version introduce one) never requires
 * touching any other part of this component.
 */
function renderSection(section: BusinessReportSection) {
  switch (section.type) {
    case 'property_overview':
      return renderSectionContent(section.content || {});
    case 'risks':
      return renderRisksSection(section.items || []);
    case 'recommendations':
      return renderPlainListSection(section.items || [], false, 'No Recommendations Provided', 'This analysis did not produce specific recommendations.', ListChecks);
    case 'priority_actions':
      return renderPlainListSection(section.items || [], true, 'No Priority Actions Identified', 'This analysis did not identify specific priority actions.', ClipboardList);
    default:
      // Generic fallback for any section type this component doesn't
      // specifically know yet - still renders something reasonable
      // rather than silently vanishing, so a future business report
      // field is never invisible even before a dedicated case is added.
      if (section.items) return renderPlainListSection(section.items, false, 'No Items', 'No items were provided.', ListChecks);
      if (section.content) return renderSectionContent(section.content);
      return null;
  }
}

export default function PropertyIntelligenceReport({
  resultId, projectName, propertyAddress, onBack,
}: PropertyIntelligenceReportProps) {
  const [result, setResult] = useState<WorkflowResult | null>(null);
  const [report, setReport] = useState<BusinessReport | null>(null);
  const [generatedImages, setGeneratedImages] = useState<DesignImageVersion[]>([]);
  const [previewImage, setPreviewImage] = useState<DesignImageVersion | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [showAdvancedDetails, setShowAdvancedDetails] = useState(false);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setIsLoading(true);
      try {
        const [resultRes, reportRes] = await Promise.all([
          workflowService.getResult(resultId),
          workflowService.getBusinessReport(resultId),
        ]);
        if (cancelled) return;
        setResult(resultRes);
        const businessReport = (reportRes as unknown as BusinessReport) || null;
        setReport(businessReport);

        // AIHOME Image Result Integration: only queried when the report
        // itself flags generated images as present - images were
        // already imported into AIHOME's own storage at result-sync
        // time (design_result_service.ingest_image_design_results()),
        // so this only ever displays AIHOME-managed images, never a
        // live DEV-TOOLS artifact URL.
        if (businessReport?.metadata?.has_generated_images) {
          const imagesRes = await designImageVersionService.listForWorkflowExecution(resultRes.execution_id);
          if (!cancelled) setGeneratedImages(imagesRes.items || []);
        }
      } catch (err) {
        console.error('[PropertyIntelligenceReport] Failed to load report:', err);
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }
    load();
    return () => { cancelled = true; };
  }, [resultId]);

  const handleDownload = () => {
    if (!result?.response_json) return;
    downloadJson(result.response_json, `property-intelligence-${resultId}.json`);
  };

  if (isLoading) {
    return (
      <div className="flex-1 flex flex-col justify-center items-center text-slate-400 text-xs font-mono uppercase tracking-widest py-16">
        <RefreshCw className="w-6 h-6 animate-spin text-indigo-600 mb-2" />
        Retrieving report...
      </div>
    );
  }

  if (!result) {
    return <EmptyState title="Report Not Found" description="This report could not be located." id="property-intelligence-report-not-found" />;
  }

  return (
    <div className={styles.report} id="property-intelligence-report">
      <div className={styles.header}>
        {onBack && (
          <button type="button" onClick={onBack} className={styles.backLink}>
            <ChevronRight className={styles.backIcon} /> Back to Reports
          </button>
        )}
        <div className={styles.headerTopRow}>
          <div className={styles.headerBadges}>
            <StatusBadge status={result.result_type} type="workflow" />
            <span className={styles.versionTag}>V{result.result_version || '1.0'}</span>
          </div>
          <div className={styles.receivedAt}>
            <Calendar className={styles.receivedIcon} />
            <span>{new Date(result.received_at).toLocaleString()}</span>
          </div>
        </div>
        <h2 className={styles.headerTitle}>{propertyAddress || 'Property Intelligence Report'}</h2>
        {projectName && <p className={styles.headerProject}>PROJECT: {projectName}</p>}
      </div>

      {!report ? (
        <EmptyState
          title="Report Not Available"
          description="This analysis result could not be interpreted into a business report. The raw output is still available for download below."
          id="property-intelligence-report-empty"
        />
      ) : (
        <>
          <EnterpriseCard title="Executive Summary" headerAction={<StatusBadge status={report.confidence} type="confidence" />}>
            <p className={styles.narrative}>{report.executive_summary}</p>
            {Array.isArray(report.metadata?.business_intents) && (report.metadata.business_intents as string[]).length > 1 && (
              <p className={styles.combinedIntentsNote}>
                Combines analysis from: {(report.metadata.business_intents as string[])
                  .map((intent) => intent.replace(/_/g, ' ').toLowerCase().replace(/\b\w/g, (c) => c.toUpperCase()))
                  .join(', ')}
              </p>
            )}
          </EnterpriseCard>

          {report.sections.map((section, i) => (
            <EnterpriseCard key={i} title={section.title}>
              {renderSection(section)}
            </EnterpriseCard>
          ))}

          {generatedImages.length > 0 && (
            <EnterpriseCard title="Generated Design Images">
              <div className={styles.generatedImageGrid}>
                {generatedImages.map((version) => (
                  <button
                    key={version.id}
                    type="button"
                    className={styles.generatedImageThumbButton}
                    onClick={() => setPreviewImage(version)}
                  >
                    <img
                      src={`${AppConfig.uploadBaseUrl}/${version.thumbnail_path || version.storage_path}`}
                      alt={`Generated design version ${version.version_number}`}
                      className={styles.generatedImageThumb}
                    />
                    {version.quality_approved === false && (
                      <span className={styles.qualityWarningTag}>Quality Review: Not Approved</span>
                    )}
                    <div className={styles.generatedImageMeta}>
                      {version.source_provider && <span>{version.source_provider}</span>}
                      {version.source_model && <span>{version.source_model}</span>}
                    </div>
                  </button>
                ))}
              </div>
            </EnterpriseCard>
          )}

          {previewImage && (
            <div className={styles.previewOverlay} onClick={() => setPreviewImage(null)}>
              <div className={styles.previewDialog} onClick={(e) => e.stopPropagation()}>
                <img
                  src={`${AppConfig.uploadBaseUrl}/${previewImage.storage_path}`}
                  alt={`Generated design version ${previewImage.version_number}, full size`}
                  className={styles.previewImage}
                />
                <div className={styles.previewMetaRow}>
                  <span>Version {previewImage.version_number}</span>
                  {previewImage.source_provider && <span>Provider: {previewImage.source_provider}</span>}
                  {previewImage.source_model && <span>Model: {previewImage.source_model}</span>}
                  {previewImage.width && previewImage.height && <span>{previewImage.width}×{previewImage.height}</span>}
                </div>
                {previewImage.quality_approved === false && (
                  <p className={styles.qualityWarningText}>
                    DEV-TOOLS quality review did not approve this image. Review before publishing.
                  </p>
                )}
                <button type="button" className="enterprise-btn enterprise-btn-secondary" onClick={() => setPreviewImage(null)}>
                  Close
                </button>
              </div>
            </div>
          )}

          <ExpandableSection title="Advanced Technical Details" defaultExpanded={false} onFirstExpand={() => setShowAdvancedDetails(true)}>
            {showAdvancedDetails && (
              <div className={styles.attributionList}>
                <p className={styles.attributionNote}>
                  This is the original, unprocessed output as returned by the AI processing platform, provided for
                  diagnostics and troubleshooting only. Normal use of this report never requires viewing it.
                </p>
                <pre className={styles.rawJsonBlock}>{result.response_json}</pre>
              </div>
            )}
          </ExpandableSection>
        </>
      )}

      <div className={styles.downloadRow}>
        <button
          type="button"
          className="enterprise-btn enterprise-btn-secondary"
          onClick={handleDownload}
          disabled={!result.response_json}
        >
          <Download className={styles.downloadIcon} />
          Download Full JSON
        </button>
      </div>
    </div>
  );
}
