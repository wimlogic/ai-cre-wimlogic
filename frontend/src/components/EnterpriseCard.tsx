import React from 'react';

export interface EnterpriseCardProps {
  children: React.ReactNode;
  title?: string | React.ReactNode;
  subtitle?: string | React.ReactNode;
  headerAction?: React.ReactNode;
  footer?: React.ReactNode;
  className?: string;
  id?: string;
}

export default function EnterpriseCard({
  children,
  title,
  subtitle,
  headerAction,
  footer,
  className = '',
  id,
}: EnterpriseCardProps) {
  const hasHeader = title || subtitle || headerAction;

  return (
    <div id={id || 'enterprise-card'} className={`enterprise-card ${className}`}>
      {hasHeader && (
        <div className="px-5 py-4 border-b border-slate-100 flex items-center justify-between gap-4">
          <div className="space-y-0.5">
            {title && (
              <h3 className="text-xs font-bold text-slate-900 uppercase tracking-widest font-mono">
                {title}
              </h3>
            )}
            {subtitle && (
              <p className="text-[11px] text-slate-500 leading-normal">
                {subtitle}
              </p>
            )}
          </div>
          {headerAction && <div className="shrink-0">{headerAction}</div>}
        </div>
      )}
      <div className="p-5">{children}</div>
      {footer && (
        <div className="px-5 py-3.5 bg-slate-50/80 border-t border-slate-100 flex items-center justify-between gap-4">
          {footer}
        </div>
      )}
    </div>
  );
}
