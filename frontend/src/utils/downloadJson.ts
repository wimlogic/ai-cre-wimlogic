/**
 * utils/downloadJson.ts
 *
 * Shared by AnalysisReportView.tsx's existing Download JSON action and the
 * new PropertyIntelligenceReport renderer, rather than each keeping its
 * own copy of the same blob/anchor logic.
 */
export function downloadJson(rawJsonString: string, filename: string): void {
  let content = rawJsonString;
  try {
    content = JSON.stringify(JSON.parse(rawJsonString), null, 2);
  } catch {
    // Malformed JSON - download exactly what's stored rather than failing silently.
  }
  const blob = new Blob([content], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}
