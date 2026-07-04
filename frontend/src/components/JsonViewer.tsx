import React, { useState } from 'react';
import { Copy, Check, Eye, EyeOff } from 'lucide-react';

export interface JsonViewerProps {
  data: any;
  title?: string;
  id?: string;
}

export default function JsonViewer({ data, title = 'JSON Payload', id }: JsonViewerProps) {
  const [copied, setCopied] = useState(false);
  const [expanded, setExpanded] = useState(true);

  if (!data) return null;

  const jsonString = typeof data === 'string' ? data : JSON.stringify(data, null, 2);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(jsonString);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy JSON:', err);
    }
  };

  return (
    <div
      id={id || 'json-viewer-card'}
      className="enterprise-card overflow-hidden border border-slate-200"
    >
      <div className="px-4 py-2.5 bg-slate-900 border-b border-slate-800 flex items-center justify-between text-white select-none">
        <span className="text-[10px] font-bold tracking-widest font-mono uppercase text-slate-400">
          {title}
        </span>
        <div className="flex items-center gap-1.5">
          <button
            onClick={() => setExpanded(!expanded)}
            className="p-1 text-slate-400 hover:text-white rounded transition-colors focus:outline-none"
            title={expanded ? 'Collapse' : 'Expand'}
          >
            {expanded ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
          </button>
          <button
            onClick={handleCopy}
            className="p-1 text-slate-400 hover:text-white rounded transition-colors focus:outline-none"
            title="Copy JSON"
          >
            {copied ? <Check className="w-3.5 h-3.5 text-emerald-400 animate-pulse" /> : <Copy className="w-3.5 h-3.5" />}
          </button>
        </div>
      </div>
      {expanded && (
        <pre className="p-4 bg-slate-950 text-emerald-400 text-[11px] font-mono overflow-auto max-h-[300px] leading-relaxed">
          <code>{jsonString}</code>
        </pre>
      )}
    </div>
  );
}
