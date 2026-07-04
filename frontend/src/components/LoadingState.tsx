import React from 'react';
import { Loader2 } from 'lucide-react';

export interface LoadingStateProps {
  message?: string;
  type?: 'spinner' | 'skeleton' | 'rows';
  rowsCount?: number;
  id?: string;
}

export default function LoadingState({
  message = 'Loading data...',
  type = 'spinner',
  rowsCount = 5,
  id,
}: LoadingStateProps) {
  if (type === 'skeleton') {
    return (
      <div id={id || 'loading-skeleton'} className="space-y-4 w-full animate-pulse">
        <div className="h-8 bg-slate-200/80 rounded w-1/4" />
        <div className="space-y-2">
          <div className="h-4 bg-slate-200/80 rounded" />
          <div className="h-4 bg-slate-200/80 rounded w-5/6" />
          <div className="h-4 bg-slate-200/80 rounded w-2/3" />
        </div>
      </div>
    );
  }

  if (type === 'rows') {
    return (
      <div id={id || 'loading-rows'} className="space-y-3 w-full">
        {Array.from({ length: rowsCount }).map((_, index) => (
          <div
            key={index}
            className="flex items-center justify-between p-4 enterprise-card bg-white animate-pulse"
          >
            <div className="flex items-center gap-3 w-full">
              <div className="w-8 h-8 bg-slate-100 rounded-full shrink-0" />
              <div className="space-y-1.5 w-full">
                <div className="h-3 bg-slate-200 rounded w-1/3" />
                <div className="h-2.5 bg-slate-150 rounded w-1/2" />
              </div>
            </div>
          </div>
        ))}
      </div>
    );
  }

  return (
    <div
      id={id || 'loading-spinner'}
      className="flex flex-col items-center justify-center py-12 text-center"
    >
      <Loader2 className="w-8 h-8 text-indigo-600 animate-spin" />
      <p className="text-xs font-semibold text-slate-500 mt-3">{message}</p>
    </div>
  );
}
