import { useState, useEffect } from 'react';
import { workflowService } from '../services/workflowService';
import { generatedAssetService } from '../services/generatedAssetService';
import { WorkflowResult, ResultSection, GeneratedAsset } from '../types/index';
import {
  Download, ExternalLink, ChevronRight, Calendar, Copy, Check, RefreshCw, FileSpreadsheet,
} from 'lucide-react';

/**
 * components/AnalysisReportView.tsx
 *
 * Phase 2B - extracted verbatim (not reimplemented) from
 * pages/WorkflowResults.tsx's natural-language report rendering: the six
 * sections (Executive Summary through Conclusion) with correct list-vs-
 * paragraph treatment, missing-section hiding, malformed-output
 * fallback, Copy Report, Download JSON, and the Raw JSON / Deliverables
 * tabs. Reusable so it renders identically whether opened from a
 * Property's Reports tab (this phase) or the global Reports catalog
 * (Phase 2C, where WorkflowResults.tsx is refactored to consume this
 * same component rather than keeping its own duplicate copy).
 *
 * Deliberately does NOT include the result-sync-error banner/Retry Sync
 * control the original inline version had: by construction, this
 * component is only ever reached via a "View Report"/"Open Report"
 * action, which (per resolveExecutionRowState, Phase 2A) is only ever
 * offered for an execution that already has a successfully-synced
 * report. A sync-failed execution shows "Retry Sync" at the list level
 * and never reaches this component at all - carrying the banner here
 * too would be dead code for a state this component structurally cannot
 * be opened from.
 */

/**
 * Mirrors app/services/result_sync.py's _NL_REPORT_FIELDS /
 * _NL_REPORT_LIST_FIELDS / _NL_REPORT_TITLES / _NL_REPORT_DISPLAY_ORDER
 * exactly, unchanged from the original inline version.
 */
const NL_REPORT_FIELD_ORDER = [
  'executive_summary', 'key_findings', 'business_health',
  'priority_actions', 'recommendations', 'conclusion',
];
const NL_REPORT_LIST_FIELDS = new Set(['key_findings', 'priority_actions', 'recommendations']);
const NL_REPORT_TITLES: Record<string, string> = {
  executive_summary: 'Executive Summary',
  key_findings: 'Key Findings',
  business_health: 'Business Health',
  priority_actions: 'Priority Actions',
  recommendations: 'Recommendations',
  conclusion: 'Conclusion',
};

function parseSectionForDisplay(sec: ResultSection): { isList: boolean; items: string[]; text: string } {
  const isListField = NL_REPORT_LIST_FIELDS.has(sec.section_type);
  if (isListField) {
    try {
      const parsed = JSON.parse(sec.content || '[]');
      if (Array.isArray(parsed)) {
        return { isList: true, items: parsed.map((i) => String(i)), text: '' };
      }
    } catch {
      // Malformed - fall through to plain-text fallback below.
    }
  }
  return { isList: false, items: [], text: sec.content || '' };
}

function buildReportPlainText(sections: ResultSection[]): string {
  const bySectionType = new Map(sections.map((s) => [s.section_type, s]));
  const lines: string[] = [];
  for (const field of NL_REPORT_FIELD_ORDER) {
    const sec = bySectionType.get(field);
    if (!sec) continue;
    lines.push(NL_REPORT_TITLES[field], '');
    const { isList, items, text } = parseSectionForDisplay(sec);
    if (isList) {
      items.forEach((item) => lines.push(`- ${item}`));
    } else {
      lines.push(text);
    }
    lines.push('');
  }
  return lines.join('\n').trim();
}

export interface AnalysisReportViewProps {
  /** WorkflowResult.result_id - the one piece of data this component
   * doesn't already receive from its caller (Sections, and the parent
   * WorkflowResult record itself, are fetched internally). */
  resultId: number;
  /** Already known by every caller (the Property page already has its
   * own property loaded; the global Reports catalog already resolves
   * this today) - passed in rather than re-fetched, to avoid redundant
   * calls when embedded in a context that already has the answer. */
  projectName?: string;
  propertyAddress?: string;
  onBack?: () => void;
}

export default function AnalysisReportView({ resultId, projectName, propertyAddress, onBack }: AnalysisReportViewProps) {
  const [result, setResult] = useState<WorkflowResult | null>(null);
  const [sections, setSections] = useState<ResultSection[]>([]);
  const [assets, setAssets] = useState<GeneratedAsset[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'summary' | 'sections' | 'raw' | 'assets'>('summary');
  const [copiedReport, setCopiedReport] = useState(false);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setIsLoading(true);
      try {
        const [resultRes, sectionsRes] = await Promise.all([
          workflowService.getResult(resultId),
          workflowService.getResultSections(resultId),
        ]);
        if (cancelled) return;
        setResult(resultRes);
        setSections(sectionsRes.items || []);
        const assetsRes = await generatedAssetService.list({ execution_id: resultRes.execution_id }).catch(() => ({ items: [] }));
        if (!cancelled) setAssets(assetsRes.items || []);
      } catch (err) {
        console.error('[AnalysisReportView] Failed to load report:', err);
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }
    load();
    return () => { cancelled = true; };
  }, [resultId]);

  const handleCopyReport = async () => {
    const text = buildReportPlainText(sections);
    try {
      await navigator.clipboard.writeText(text);
      setCopiedReport(true);
      setTimeout(() => setCopiedReport(false), 2000);
    } catch (err) {
      console.error('Copy to clipboard failed:', err);
    }
  };

  const handleDownloadJson = () => {
    if (!result?.response_json) return;
    let content = result.response_json;
    try {
      content = JSON.stringify(JSON.parse(result.response_json), null, 2);
    } catch {
      // Malformed JSON - download exactly what's stored rather than failing silently.
    }
    const blob = new Blob([content], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `analysis-report-${resultId}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  if (isLoading) {
    return (
      <div className="flex-1 flex flex-col justify-center items-center text-slate-400 text-xs font-mono uppercase tracking-widest py-16">
        <RefreshCw className="w-6 h-6 animate-spin text-indigo-600 mb-2" />
        Retrieving report packets...
      </div>
    );
  }

  if (!result) {
    return <div className="text-center text-slate-400 py-12 italic font-mono uppercase">Report not found.</div>;
  }

  const bySectionType = new Map(sections.map((s) => [s.section_type, s]));
  const reportSections = NL_REPORT_FIELD_ORDER.map((field) => bySectionType.get(field)).filter((s): s is ResultSection => Boolean(s));

  return (
    <div className="space-y-6 flex-1 flex flex-col" id="analysis-report-view">
      <div className="border-b border-slate-100 pb-4 shrink-0">
        {onBack && (
          <button onClick={onBack} className="text-xs font-semibold text-indigo-600 hover:text-indigo-800 mb-2 flex items-center gap-1">
            <ChevronRight className="w-3.5 h-3.5 rotate-180" /> Back to Reports
          </button>
        )}
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <span className="px-2.5 py-0.5 bg-indigo-600 text-white rounded text-[10px] font-mono font-bold uppercase tracking-wider">
              {result.result_type} REPORT
            </span>
            <span className="text-xs font-mono text-slate-400">V{result.result_version || '1.0'}</span>
          </div>
          <div className="flex items-center gap-1 text-[10px] font-mono text-slate-400">
            <Calendar className="w-3.5 h-3.5" />
            <span>{new Date(result.received_at).toLocaleString()}</span>
          </div>
        </div>

        <h2 className="text-base font-sans font-bold text-slate-800 mt-2">{propertyAddress || 'Analytical Dossier'}</h2>
        {projectName && (
          <p className="text-[11px] font-mono text-indigo-600 mt-1 uppercase">PROJECT: {projectName}</p>
        )}

        <div className="flex items-center gap-2 mt-3">
          <button
            onClick={handleCopyReport}
            disabled={sections.length === 0}
            className="flex items-center gap-1.5 px-2.5 py-1.5 border border-slate-200 hover:bg-slate-50 text-slate-600 rounded-lg text-[11px] font-semibold transition-colors focus:outline-none disabled:opacity-40"
          >
            {copiedReport ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <Copy className="w-3.5 h-3.5" />}
            {copiedReport ? 'Copied' : 'Copy Report'}
          </button>
          <button
            onClick={handleDownloadJson}
            disabled={!result.response_json}
            className="flex items-center gap-1.5 px-2.5 py-1.5 border border-slate-200 hover:bg-slate-50 text-slate-600 rounded-lg text-[11px] font-semibold transition-colors focus:outline-none disabled:opacity-40"
          >
            <Download className="w-3.5 h-3.5" />
            Download JSON
          </button>
        </div>
      </div>

      <div className="flex border-b border-slate-100 gap-4 text-xs font-semibold tracking-wide shrink-0">
        {(['summary', 'sections', 'raw', 'assets'] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`pb-2.5 px-1 border-b-2 transition-all focus:outline-none ${
              activeTab === tab ? 'border-indigo-600 text-slate-900' : 'border-transparent text-slate-400 hover:text-slate-600'
            }`}
          >
            {tab === 'summary' && 'Executive Summary'}
            {tab === 'sections' && `Report Sections (${sections.length})`}
            {tab === 'raw' && 'Raw API JSON'}
            {tab === 'assets' && `Deliverables (${assets.length})`}
          </button>
        ))}
      </div>

      <div className="flex-1 overflow-y-auto">
        {activeTab === 'summary' && (
          reportSections.length > 0 ? (
            <div className="space-y-6 text-slate-700 leading-relaxed text-xs">
              {reportSections.map((sec) => {
                const { isList, items, text } = parseSectionForDisplay(sec);
                return (
                  <div key={sec.section_id} className="space-y-2">
                    <h3 className="font-sans font-bold text-slate-800 text-sm border-b border-slate-50 pb-2">
                      {NL_REPORT_TITLES[sec.section_type] || sec.title}
                    </h3>
                    {isList ? (
                      <ul className="list-disc list-inside space-y-1 text-slate-600">
                        {items.map((item, i) => <li key={i}>{item}</li>)}
                      </ul>
                    ) : (
                      <p className="whitespace-pre-line text-slate-600">{text}</p>
                    )}
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="space-y-4 text-slate-700 leading-relaxed text-xs">
              {sections.length > 0 ? (
                <div className="space-y-4">
                  <h3 className="font-sans font-bold text-slate-800 text-sm border-b border-slate-50 pb-2">
                    {sections[0].title || 'Primary Analysis Overview'}
                  </h3>
                  <p className="whitespace-pre-line text-slate-600">{sections[0].content}</p>
                </div>
              ) : (
                <div className="text-slate-400 italic py-10 text-center font-mono uppercase">
                  No report summaries found in results database.
                </div>
              )}
            </div>
          )
        )}

        {activeTab === 'sections' && (
          <div className="space-y-5">
            {sections.length === 0 ? (
              <div className="text-center text-slate-400 py-12 italic font-mono uppercase">No parsed section data recorded.</div>
            ) : (
              sections.map((sec) => {
                const { isList, items, text } = parseSectionForDisplay(sec);
                return (
                  <div key={sec.section_id} className="border border-slate-100 rounded-lg p-4 space-y-2">
                    <div className="flex justify-between items-center">
                      <span className="text-[10px] font-mono font-bold text-slate-400 uppercase">SECTION TYPE: {sec.section_type}</span>
                      {sec.confidence_score !== undefined && (
                        <span className="px-1.5 py-0.5 rounded bg-emerald-50 text-emerald-800 text-[9px] font-mono font-bold">
                          CONFIDENCE: {Math.round(sec.confidence_score * 100)}%
                        </span>
                      )}
                    </div>
                    <h3 className="font-sans font-bold text-slate-800 text-xs uppercase tracking-wide">
                      {NL_REPORT_TITLES[sec.section_type] || sec.title}
                    </h3>
                    {isList ? (
                      <ul className="list-disc list-inside space-y-1 text-xs text-slate-600 leading-relaxed">
                        {items.map((item, i) => <li key={i}>{item}</li>)}
                      </ul>
                    ) : (
                      <p className="text-xs text-slate-600 leading-relaxed whitespace-pre-line">{text}</p>
                    )}
                  </div>
                );
              })
            )}
          </div>
        )}

        {activeTab === 'raw' && (
          <div className="bg-slate-950 text-emerald-400 font-mono text-xs rounded-xl p-4 overflow-x-auto max-h-[50vh]">
            <pre className="whitespace-pre-wrap leading-tight">
              {result.response_json ? (
                (() => {
                  try { return JSON.stringify(JSON.parse(result.response_json), null, 2); }
                  catch { return result.response_json; }
                })()
              ) : '// No payload JSON data returned.'}
            </pre>
          </div>
        )}

        {activeTab === 'assets' && (
          <div className="space-y-3">
            {assets.length === 0 ? (
              <div className="text-center text-slate-400 py-12 italic font-mono uppercase">
                No attached deliverable documents or CAD charts.
              </div>
            ) : (
              assets.map((asset) => (
                <div key={asset.asset_id} className="border border-slate-100 rounded-lg p-4 flex items-center justify-between group hover:border-slate-200 hover:bg-slate-50 transition-all">
                  <div className="flex items-center gap-3">
                    <div className="p-2.5 bg-indigo-50 text-indigo-600 rounded-lg shrink-0">
                      <FileSpreadsheet className="w-5 h-5" />
                    </div>
                    <div>
                      <h4 className="font-sans font-bold text-slate-800 text-xs group-hover:text-indigo-600 transition-colors">
                        {asset.title || asset.file_name}
                      </h4>
                      <p className="text-[10px] font-mono text-slate-400 uppercase mt-0.5">
                        CATEGORY: {asset.asset_type} ({asset.file_size ? `${Math.round(asset.file_size / 1024)} KB` : 'Unknown size'})
                      </p>
                    </div>
                  </div>
                  {asset.storage_path && (
                    <a href={asset.storage_path} target="_blank" rel="noopener noreferrer" className="p-2 text-slate-400 hover:text-indigo-600">
                      <ExternalLink className="w-4 h-4" />
                    </a>
                  )}
                </div>
              ))
            )}
          </div>
        )}
      </div>
    </div>
  );
}
