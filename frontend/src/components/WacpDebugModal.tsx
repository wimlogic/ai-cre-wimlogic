import { useEffect, useRef, useState } from 'react';
import { apiClient } from '../services/apiClient';
import { Copy, Check, Send } from 'lucide-react';
import styles from './WacpDebugModal.module.css';

/**
 * components/WacpDebugModal.tsx
 *
 * TEMPORARY DEBUGGING FEATURE - routing verification.
 *
 * Polls GET /api/v1/wacp-debug/pending. When the backend has a job
 * submission paused (app/services/wacp_debug_intercept.py), shows the
 * EXACT captured request body - the `pretty` string returned by that
 * endpoint is already `json.dumps(json_body, indent=2)` of the literal
 * object about to be handed to the HTTP client; this component renders
 * it verbatim in a <pre> and never re-serializes, reformats, or
 * reconstructs it in any way.
 *
 * With the backend's WACP_DEBUG_INTERCEPT setting left at its default
 * (False), every poll gets a 404 and this component renders nothing -
 * safe to mount permanently without its own separate feature flag.
 *
 * To remove this feature entirely once the routing issue it exists to
 * diagnose is resolved: delete this file, its CSS module, the one
 * mount point wherever it was added, and the backend pieces listed in
 * wacp_debug_intercept.py's own docstring.
 */

interface PendingWacpRequest {
  request_id: string;
  path: string;
  pretty: string;
}

const POLL_INTERVAL_MS = 1000;

export default function WacpDebugModal() {
  const [pending, setPending] = useState<PendingWacpRequest | null>(null);
  const [copied, setCopied] = useState(false);
  const [isContinuing, setIsContinuing] = useState(false);
  const currentRequestIdRef = useRef<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    const poll = async () => {
      try {
        const res = await apiClient.get<{ items: PendingWacpRequest[] }>('/wacp-debug/pending');
        if (cancelled) return;
        const next = res.items?.[0] || null;
        // Only replace state (and reset "Copied") when the actual
        // pending request changes - avoids flicker/reset on every poll
        // tick while the same request is still waiting.
        if (next?.request_id !== currentRequestIdRef.current) {
          currentRequestIdRef.current = next?.request_id || null;
          setPending(next);
          setCopied(false);
        }
      } catch {
        // 404 (feature disabled) or a transient network error - either
        // way, render nothing. This is a debug aid, not core
        // functionality; it must never surface an error to the user.
        if (!cancelled && currentRequestIdRef.current !== null) {
          currentRequestIdRef.current = null;
          setPending(null);
        }
      }
    };

    poll();
    const interval = setInterval(poll, POLL_INTERVAL_MS);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, []);

  if (!pending) return null;

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(pending.pretty);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('[WacpDebugModal] Copy failed:', err);
    }
  };

  const handleContinue = async () => {
    setIsContinuing(true);
    try {
      await apiClient.post(`/wacp-debug/pending/${encodeURIComponent(pending.request_id)}/continue`, {});
    } catch (err) {
      console.error('[WacpDebugModal] Continue Sending failed:', err);
    } finally {
      setIsContinuing(false);
    }
  };

  // Logged to the console verbatim, identical to what's displayed and
  // identical to what the backend captured - per requirement #5.
  // eslint-disable-next-line no-console
  console.log('WACP Request (Exact HTTP Body) - request_id=' + pending.request_id + '\n' + pending.pretty);

  return (
    <div className={styles.overlay}>
      <div className={styles.dialog} role="dialog" aria-modal="true" aria-labelledby="wacp-debug-title">
        <div className={styles.header}>
          <h2 id="wacp-debug-title" className={styles.title}>WACP Request (Exact HTTP Body)</h2>
          <span className={styles.pathTag}>POST {pending.path}</span>
        </div>
        <p className={styles.note}>
          This is the literal request body already built and about to be sent to DEV-TOOLS - captured at the
          HTTP client call site, not reconstructed. Nothing is modified by viewing it.
        </p>
        <pre className={styles.jsonBlock}>{pending.pretty}</pre>
        <div className={styles.actions}>
          <button type="button" className="enterprise-btn enterprise-btn-secondary" onClick={handleCopy}>
            {copied ? <Check className={styles.icon} /> : <Copy className={styles.icon} />}
            {copied ? 'Copied' : 'Copy JSON'}
          </button>
          <button type="button" className="enterprise-btn enterprise-btn-primary" onClick={handleContinue} disabled={isContinuing}>
            <Send className={styles.icon} />
            {isContinuing ? 'Sending...' : 'Continue Sending'}
          </button>
        </div>
      </div>
    </div>
  );
}
