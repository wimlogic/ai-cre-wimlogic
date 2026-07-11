import { AlertTriangle, HelpCircle } from 'lucide-react';
import styles from './ConfirmDialog.module.css';

export interface ConfirmDialogProps {
  isOpen: boolean;
  title: string;
  message: string;
  confirmLabel?: string;
  cancelLabel?: string;
  onConfirm: () => void;
  onCancel: () => void;
  isDanger?: boolean;
  id?: string;
}

export default function ConfirmDialog({
  isOpen,
  title,
  message,
  confirmLabel = 'Confirm',
  cancelLabel = 'Cancel',
  onConfirm,
  onCancel,
  isDanger = false,
  id,
}: ConfirmDialogProps) {
  if (!isOpen) return null;

  return (
    <div
      id={id || 'confirm-dialog-overlay'}
      className="enterprise-dialog-overlay"
      onClick={onCancel}
    >
      <div
        id={id ? `${id}-content` : 'confirm-dialog-content'}
        className="enterprise-dialog-panel"
        style={{ maxWidth: '28rem' }}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="enterprise-dialog-body">
          <div className={styles.bodyRow}>
            <div className={`${styles.iconWrap} ${isDanger ? styles.iconWrapDanger : styles.iconWrapNeutral}`}>
              {isDanger ? <AlertTriangle className={styles.icon} /> : <HelpCircle className={styles.icon} />}
            </div>
            <div className={styles.textGroup}>
              <h3 className="enterprise-dialog-title">{title}</h3>
              <p className={styles.message}>{message}</p>
            </div>
          </div>
        </div>

        <div className="enterprise-dialog-footer">
          <button
            onClick={onCancel}
            className="enterprise-btn enterprise-btn-secondary"
            id={id ? `${id}-cancel` : 'confirm-dialog-btn-cancel'}
          >
            {cancelLabel}
          </button>
          <button
            onClick={onConfirm}
            className={`enterprise-btn ${isDanger ? 'enterprise-btn-danger' : 'enterprise-btn-primary'}`}
            id={id ? `${id}-confirm` : 'confirm-dialog-btn-confirm'}
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
