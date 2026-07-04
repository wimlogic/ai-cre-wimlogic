import React from 'react';
import { LucideIcon, FileX } from 'lucide-react';

export interface EmptyStateProps {
  title: string;
  description: string;
  icon?: LucideIcon;
  actionLabel?: string;
  onAction?: () => void;
  id?: string;
}

export default function EmptyState({
  title,
  description,
  icon: Icon = FileX,
  actionLabel,
  onAction,
  id,
}: EmptyStateProps) {
  return (
    <div
      id={id || 'enterprise-empty-state'}
      className="flex flex-col items-center justify-center text-center p-8 md:p-12 enterprise-card border-dashed bg-slate-50/30"
    >
      <div className="w-12 h-12 rounded-full bg-slate-100 flex items-center justify-center text-slate-400 mb-4">
        <Icon className="w-6 h-6" />
      </div>
      <h3 className="text-sm font-semibold text-slate-800 tracking-tight">{title}</h3>
      <p className="text-xs text-slate-500 max-w-sm mt-1 mb-5 leading-relaxed">{description}</p>
      {actionLabel && onAction && (
        <button
          id={id ? `${id}-action` : 'empty-state-action'}
          onClick={onAction}
          className="enterprise-btn enterprise-btn-primary"
        >
          {actionLabel}
        </button>
      )}
    </div>
  );
}
