import { useState } from 'react';
import { Copy, Check, Eye, EyeOff } from 'lucide-react';
import styles from './JsonViewer.module.css';

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
    <div id={id || 'json-viewer-card'} className={`enterprise-card ${styles.wrapper}`}>
      <div className={styles.header}>
        <span className={styles.title}>{title}</span>
        <div className={styles.actions}>
          <button
            onClick={() => setExpanded(!expanded)}
            className={styles.actionBtn}
            title={expanded ? 'Collapse' : 'Expand'}
          >
            {expanded ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
          </button>
          <button onClick={handleCopy} className={styles.actionBtn} title="Copy JSON">
            {copied ? (
              <Check className={`w-3.5 h-3.5 ${styles.copiedIcon}`} />
            ) : (
              <Copy className="w-3.5 h-3.5" />
            )}
          </button>
        </div>
      </div>
      {expanded && (
        <pre className={styles.codeBlock}>
          <code>{jsonString}</code>
        </pre>
      )}
    </div>
  );
}
