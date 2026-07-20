import React, { useState, useEffect } from 'react';
import { workflowService } from '../services/workflowService';
import { generatedAssetService } from '../services/generatedAssetService';
import { projectService } from '../services/projectService';
import { propertyService } from '../services/propertyService';
// Explicit '../types/index' path: '../types' currently resolves to the
// legacy types.ts sibling file under this project's bundler resolution,
// which does not export these names. Pre-existing issue, deferred to
// Phase 1C - Type Architecture Cleanup (see AIOrchestration.tsx /
// EnterpriseJobPanel.tsx for the same documented workaround).
import { WorkflowResult, ResultSection, GeneratedAsset, WorkflowExecution } from '../types/index';
import StatusBadge from '../components/StatusBadge';
import {
  FileSpreadsheet, 
  RefreshCw, 
  Layers, 
  Code, 
  FileCheck, 
  Download, 
  ExternalLink,
  ChevronRight,
  Info,
  Calendar,
  Sparkles,
  ClipboardList,
  AlertCircle,
  Copy,
  Check,
} from 'lucide-react';

/**
 * Mirrors app/services/result_sync.py's _NL_REPORT_FIELDS /
 * _NL_REPORT_LIST_FIELDS / _NL_REPORT_TITLES / _NL_REPORT_DISPLAY_ORDER
 * exactly - the backend is the single source of truth for which
 * section_types exist, their display order, and which render as lists
 * vs paragraphs; this is kept in sync with that, not independently
 * decided on the frontend.
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

/** Parses a ResultSection's content for display. List-type sections are
 * stored as a JSON array string; a parse failure there (malformed
 * output) falls back to showing the raw stored text as a single
 * "paragraph" rather than crashing the page. */
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

/** Builds a single, readable plain-text version of the natural-language
 * report for the "Copy Report" action - list sections become "- item"
 * lines, paragraph sections stay as prose, in the fixed reading order. */
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

export default function WorkflowResults() {
  const [results, setResults] = useState<WorkflowResult[]>([]);
  const [selectedResult, setSelectedResult] = useState<WorkflowResult | null>(null);
  
  // Details related to selected result
  const [sections, setSections] = useState<ResultSection[]>([]);
  const [assets, setAssets] = useState<GeneratedAsset[]>([]);
  const [execution, setExecution] = useState<WorkflowExecution | null>(null);
  const [projName, setProjName] = useState('');
  const [propAddress, setPropAddress] = useState('');

  const [isLoadingList, setIsLoadingList] = useState(true);
  const [isLoadingDetails, setIsLoadingDetails] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');
  const [activeTab, setActiveTab] = useState<'summary' | 'sections' | 'raw' | 'assets'>('summary');
  const [copiedReport, setCopiedReport] = useState(false);
  const [isRetryingSync, setIsRetryingSync] = useState(false);

  /**
   * Loads the results catalog. This is the same function a future
   * EnterpriseJobContext subscriber would call on a JobCompletedEvent to
   * auto-refresh this page - see the Phase 1A assessment's deferred
   * cross-page refresh item. No such subscription exists yet, so this page
   * still only refreshes on mount and on manual "Refresh results" clicks,
   * exactly as before.
   */
  const loadResults = async () => {
    setIsLoadingList(true);
    setErrorMsg('');
    try {
      const res = await workflowService.listResults({ limit: 50 });
      setResults(res.items || []);
      if (res.items.length > 0) {
        handleSelectResult(res.items[0]);
      }
    } catch (err) {
      console.error('Failed to load workflow results:', err);
      setErrorMsg('Error loading results catalog from the backend server.');
    } finally {
      setIsLoadingList(false);
    }
  };

  useEffect(() => {
    loadResults();
  }, []);

  const handleSelectResult = async (res: WorkflowResult) => {
    setSelectedResult(res);
    setIsLoadingDetails(true);
    setSections([]);
    setAssets([]);
    setExecution(null);
    setProjName('');
    setPropAddress('');

    try {
      // 1. Fetch related sections
      const sectionsRes = await workflowService.getResultSections(res.result_id);
      setSections(sectionsRes.items || []);

      // 2. Fetch related assets
      const assetsRes = await generatedAssetService.list({ execution_id: res.execution_id });
      setAssets(assetsRes.items || []);

      // 3. Fetch related execution to map project / property metadata
      const exec = await workflowService.getExecution(res.execution_id);
      setExecution(exec);

      // 4. Resolve names
      if (exec.project_id) {
        const proj = await projectService.get(exec.project_id).catch(() => null);
        if (proj) setProjName(proj.project_name);
      }
      if (exec.property_id) {
        const prop = await propertyService.get(exec.property_id).catch(() => null);
        if (prop) setPropAddress(prop.address || '');
      }

    } catch (err) {
      console.error('Failed to load result deep details:', err);
    } finally {
      setIsLoadingDetails(false);
    }
  };

  /**
   * Retries result synchronization only - calls the exact same status-
   * check endpoint the normal polling path already uses
   * (GET /ai-orchestration/status/{execution_id}). If the prior attempt
   * failed after DEV-TOOLS had already completed the job remotely, this
   * re-attempts the fetch+sync step only; it never resubmits the
   * workflow (that would call POST /ai-orchestration/submit, a
   * completely different endpoint this button never touches).
   */
  const handleRetrySync = async () => {
    if (!execution) return;
    setIsRetryingSync(true);
    try {
      await workflowService.checkStatus(execution.execution_id);
      if (selectedResult) {
        await handleSelectResult(selectedResult);
      }
      await loadResults();
    } catch (err) {
      console.error('Retry sync failed:', err);
    } finally {
      setIsRetryingSync(false);
    }
  };

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
    if (!selectedResult?.response_json) return;
    let content = selectedResult.response_json;
    try {
      content = JSON.stringify(JSON.parse(selectedResult.response_json), null, 2);
    } catch {
      // Malformed JSON - download exactly what's stored rather than failing silently.
    }
    const blob = new Blob([content], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `workflow-result-${selectedResult.result_id}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Page Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-xl font-sans font-bold tracking-tight text-slate-900 flex items-center gap-2">
            <ClipboardList className="w-5 h-5 text-indigo-600" />
            Workflow Results
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            Browse structured analytical payloads delivered securely from WIMLOGIC cloud.
          </p>
        </div>
        <button
          onClick={loadResults}
          className="p-2 border border-slate-200 hover:bg-slate-50 text-slate-600 rounded-lg transition-colors focus:outline-none"
          title="Refresh results"
        >
          <RefreshCw className="w-4 h-4" />
        </button>
      </div>

      {errorMsg && (
        <div className="bg-rose-50 border-l-2 border-rose-500 text-rose-800 text-xs p-3.5 rounded-lg font-medium">
          {errorMsg}
        </div>
      )}

      {isLoadingList ? (
        <div className="py-24 flex justify-center items-center text-slate-400 text-xs font-mono uppercase tracking-widest">
          Polling Results Warehouse...
        </div>
      ) : results.length === 0 ? (
        <div className="bg-white border border-slate-100 rounded-xl py-24 text-center text-slate-400 flex flex-col items-center justify-center space-y-3 shadow-sm">
          <AlertCircle className="w-10 h-10 text-slate-200" />
          <span className="text-xs font-mono uppercase tracking-wider">No results available</span>
          <p className="text-xs text-slate-400 max-w-sm">
            Launch workflow pipelines in the AI Orchestration module to generate structured results here.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          
          {/* Results Catalog sidebar */}
          <div className="lg:col-span-1 bg-white border border-slate-100 rounded-xl p-4 shadow-sm h-fit space-y-3">
            <h3 className="text-[10px] font-bold uppercase tracking-wider text-slate-400 font-mono pb-2 border-b border-slate-100">
              Delivered Payloads Catalog
            </h3>
            <div className="divide-y divide-slate-100 max-h-[70vh] overflow-y-auto space-y-2 pr-1">
              {results.map((res) => {
                const isActive = selectedResult?.result_id === res.result_id;
                return (
                  <button
                    key={res.result_id}
                    onClick={() => handleSelectResult(res)}
                    className={`w-full text-left p-3.5 rounded-lg transition-all flex items-center justify-between border ${
                      isActive 
                        ? 'bg-indigo-50 border-indigo-200 text-indigo-900 shadow-xs' 
                        : 'border-transparent hover:bg-slate-50 text-slate-700'
                    }`}
                  >
                    <div>
                      <div className="flex items-center gap-1.5">
                        <span className="text-xs font-mono font-bold uppercase tracking-wider text-indigo-600">
                          RES-{res.result_id}
                        </span>
                        <span className="px-1.5 py-0.5 rounded text-[8px] font-mono font-bold bg-slate-100 text-slate-500 uppercase">
                          {res.result_type}
                        </span>
                      </div>
                      <div className="text-[10px] text-slate-400 font-mono mt-1">
                        Execution Ref: #{res.execution_id}
                      </div>
                    </div>
                    <ChevronRight className={`w-4 h-4 text-slate-400 shrink-0 ${isActive ? 'text-indigo-600' : ''}`} />
                  </button>
                );
              })}
            </div>
          </div>

          {/* Results Details main view */}
          <div className="lg:col-span-2 bg-white border border-slate-100 rounded-xl p-5 shadow-sm flex flex-col min-h-[500px]">
            {isLoadingDetails ? (
              <div className="flex-1 flex flex-col justify-center items-center text-slate-400 text-xs font-mono uppercase tracking-widest">
                <RefreshCw className="w-6 h-6 animate-spin text-indigo-600 mb-2" />
                Retrieving report packets...
              </div>
            ) : selectedResult ? (
              <div className="space-y-6 flex-1 flex flex-col">
                {/* Result header metadata */}
                <div className="border-b border-slate-100 pb-4 shrink-0">
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div className="flex items-center gap-2">
                      <span className="px-2.5 py-0.5 bg-indigo-600 text-white rounded text-[10px] font-mono font-bold uppercase tracking-wider">
                        {selectedResult.result_type} REPORT
                      </span>
                      <span className="text-xs font-mono text-slate-400">
                        V{selectedResult.result_version || '1.0'}
                      </span>
                      {execution && <StatusBadge status={execution.status} type="workflow" />}
                    </div>
                    <div className="flex items-center gap-1 text-[10px] font-mono text-slate-400">
                      <Calendar className="w-3.5 h-3.5" />
                      <span>{new Date(selectedResult.received_at).toLocaleString()}</span>
                    </div>
                  </div>

                  <h2 className="text-base font-sans font-bold text-slate-800 mt-2">
                    {propAddress || 'Analytical Dossier'}
                  </h2>
                  <p className="text-[11px] font-mono text-indigo-600 mt-1 uppercase">
                    PROJECT: {projName || `REF:${execution?.project_id || '--'}`}
                  </p>

                  {execution?.result_sync_error && (
                    <div className="mt-3 bg-amber-50 border-l-2 border-amber-500 text-amber-900 text-xs p-3 rounded-lg flex items-center justify-between gap-3">
                      <div className="flex items-center gap-2">
                        <AlertCircle className="w-4 h-4 shrink-0" />
                        <span>
                          DEV-TOOLS completed this workflow, but AI-CRE could not retrieve or process the
                          result: {execution.result_sync_error}
                        </span>
                      </div>
                      <button
                        onClick={handleRetrySync}
                        disabled={isRetryingSync}
                        className="shrink-0 px-2.5 py-1 bg-amber-600 hover:bg-amber-700 text-white rounded-md text-[10px] font-bold uppercase tracking-wide disabled:opacity-50 focus:outline-none"
                      >
                        {isRetryingSync ? 'Retrying...' : 'Retry Sync'}
                      </button>
                    </div>
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
                      disabled={!selectedResult.response_json}
                      className="flex items-center gap-1.5 px-2.5 py-1.5 border border-slate-200 hover:bg-slate-50 text-slate-600 rounded-lg text-[11px] font-semibold transition-colors focus:outline-none disabled:opacity-40"
                    >
                      <Download className="w-3.5 h-3.5" />
                      Download JSON
                    </button>
                  </div>
                </div>

                {/* Tabs */}
                <div className="flex border-b border-slate-100 gap-4 text-xs font-semibold tracking-wide shrink-0">
                  <button
                    onClick={() => setActiveTab('summary')}
                    className={`pb-2.5 px-1 border-b-2 transition-all focus:outline-none ${
                      activeTab === 'summary' ? 'border-indigo-600 text-slate-900' : 'border-transparent text-slate-400 hover:text-slate-600'
                    }`}
                  >
                    Executive Summary
                  </button>
                  <button
                    onClick={() => setActiveTab('sections')}
                    className={`pb-2.5 px-1 border-b-2 transition-all focus:outline-none ${
                      activeTab === 'sections' ? 'border-indigo-600 text-slate-900' : 'border-transparent text-slate-400 hover:text-slate-600'
                    }`}
                  >
                    Report Sections ({sections.length})
                  </button>
                  <button
                    onClick={() => setActiveTab('raw')}
                    className={`pb-2.5 px-1 border-b-2 transition-all focus:outline-none ${
                      activeTab === 'raw' ? 'border-indigo-600 text-slate-900' : 'border-transparent text-slate-400 hover:text-slate-600'
                    }`}
                  >
                    Raw API JSON
                  </button>
                  <button
                    onClick={() => setActiveTab('assets')}
                    className={`pb-2.5 px-1 border-b-2 transition-all focus:outline-none ${
                      activeTab === 'assets' ? 'border-indigo-600 text-slate-900' : 'border-transparent text-slate-400 hover:text-slate-600'
                    }`}
                  >
                    Deliverables ({assets.length})
                  </button>
                </div>

                {/* Tab content */}
                <div className="flex-1 overflow-y-auto">
                  {/* Summary Tab */}
                  {activeTab === 'summary' && (() => {
                    const bySectionType = new Map(sections.map((s) => [s.section_type, s]));
                    const reportSections = NL_REPORT_FIELD_ORDER
                      .map((field) => bySectionType.get(field))
                      .filter((s): s is ResultSection => Boolean(s));

                    if (reportSections.length > 0) {
                      return (
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
                                    {items.map((item, i) => (
                                      <li key={i}>{item}</li>
                                    ))}
                                  </ul>
                                ) : (
                                  <p className="whitespace-pre-line text-slate-600">{text}</p>
                                )}
                              </div>
                            );
                          })}
                        </div>
                      );
                    }

                    // Backward compatibility: no natural-language report
                    // sections found - fall back to the legacy behavior
                    // of showing the first available section generically,
                    // for older result shapes this page already supported.
                    return (
                      <div className="space-y-4 text-slate-700 leading-relaxed text-xs">
                        <div className="p-4 bg-indigo-50 border border-indigo-100 rounded-xl space-y-1">
                          <h4 className="font-bold text-indigo-900 uppercase tracking-wide">Orchestrated Results Summary</h4>
                          <p className="text-indigo-950 font-medium">
                            The automation pipeline has completed successfully. Below is the processed audit timeline. Select the other tabs to inspect parsed model layers or download generated PDF reports and blueprints.
                          </p>
                        </div>
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
                    );
                  })()}

                  {/* Sections Tab */}
                  {activeTab === 'sections' && (
                    <div className="space-y-5">
                      {sections.length === 0 ? (
                        <div className="text-center text-slate-400 py-12 italic font-mono uppercase">
                          No parsed section data recorded.
                        </div>
                      ) : (
                        sections.map((sec) => {
                          const { isList, items, text } = parseSectionForDisplay(sec);
                          return (
                            <div key={sec.section_id} className="border border-slate-100 rounded-lg p-4 space-y-2">
                              <div className="flex justify-between items-center">
                                <span className="text-[10px] font-mono font-bold text-slate-400 uppercase">
                                  SECTION TYPE: {sec.section_type}
                                </span>
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
                                  {items.map((item, i) => (
                                    <li key={i}>{item}</li>
                                  ))}
                                </ul>
                              ) : (
                                <p className="text-xs text-slate-600 leading-relaxed whitespace-pre-line">
                                  {text}
                                </p>
                              )}
                            </div>
                          );
                        })
                      )}
                    </div>
                  )}

                  {/* Raw JSON Tab */}
                  {activeTab === 'raw' && (
                    <div className="bg-slate-950 text-emerald-400 font-mono text-xs rounded-xl p-4 overflow-x-auto max-h-[50vh]">
                      <pre className="whitespace-pre-wrap leading-tight">
                        {selectedResult.response_json ? (
                          (() => {
                            try {
                              return JSON.stringify(JSON.parse(selectedResult.response_json), null, 2);
                            } catch {
                              return selectedResult.response_json;
                            }
                          })()
                        ) : (
                          '// No payload JSON data returned.'
                        )}
                      </pre>
                    </div>
                  )}

                  {/* Deliverables/Assets Tab */}
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

                            <a
                              href={asset.storage_path}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="p-1.5 hover:bg-white border border-transparent hover:border-slate-200 text-slate-400 hover:text-indigo-600 rounded-lg transition-colors focus:outline-none flex items-center gap-1.5 text-xs font-semibold"
                            >
                              Open file
                              <ExternalLink className="w-3.5 h-3.5" />
                            </a>
                          </div>
                        ))
                      )}
                    </div>
                  )}
                </div>
              </div>
            ) : (
              <div className="flex-1 flex justify-center items-center text-slate-400 text-xs font-mono uppercase">
                Select a result dossier from the catalog panel.
              </div>
            )}
          </div>

        </div>
      )}
    </div>
  );
}
