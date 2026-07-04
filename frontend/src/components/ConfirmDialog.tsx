import React from 'react';
import { AlertTriangle, HelpCircle } from 'lucide-react';

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
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs transition-opacity"
    >
      <div
        id={id ? `${id}-content` : 'confirm-dialog-content'}
        className="bg-white rounded-xl shadow-xl border border-slate-200 w-full max-w-md overflow-hidden animate-fade-in"
      >
        <div className="p-6">
          <div className="flex items-start gap-4">
            <div
              className={`w-10 h-10 rounded-full flex items-center justify-center shrink-0 ${
                isDanger ? 'bg-rose-50 text-rose-600' : 'bg-indigo-50 text-indigo-600'
              }`}
            >
              {isDanger ? <AlertTriangle className="w-5 h-5" /> : <HelpCircle className="w-5 h-5" />}
            </div>
            <div className="space-y-1">
              <h3 className="text-sm font-semibold text-slate-900 tracking-tight">{title}</h3>
              <p className="text-xs text-slate-500 leading-relaxed">{message}</p>
            </div>
          </div>
        </div>

        <div className="px-6 py-4 bg-slate-50 flex items-center justify-end gap-2.5 border-t border-slate-100">
          <button
            onClick={onCancel}
            className="enterprise-btn enterprise-btn-secondary"
            id={id ? `${id}-cancel` : 'confirm-dialog-btn-cancel'}
          >
            {cancelLabel}
          </button>
          <button
            onClick={onConfirm}
            className={`
              enterprise-btn
              ${isDanger ? 'bg-rose-600 hover:bg-rose-700 text-white shadow-xs' : 'enterprise-btn-primary'}
            `}
            id={id ? `${id}-confirm` : 'confirm-dialog-btn-confirm'}
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
