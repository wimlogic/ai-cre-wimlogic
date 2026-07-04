/**
 * Enterprise status configuration and mapping utilities for the WIMLOGIC app.
 */

export type StatusVariant = 'success' | 'warning' | 'error' | 'info' | 'neutral' | 'primary';

export interface StatusConfig {
  label: string;
  variant: StatusVariant;
  bgClass: string;
  textClass: string;
  borderClass: string;
  dotClass: string;
}

const DEFAULT_STATUS_CONFIG: StatusConfig = {
  label: 'Unknown',
  variant: 'neutral',
  bgClass: 'bg-slate-50',
  textClass: 'text-slate-600',
  borderClass: 'border-slate-200/80',
  dotClass: 'bg-slate-400',
};

/**
 * Enterprise maps for various statuses used in the platform
 */
export const PROJECT_STATUS_MAP: Record<string, StatusConfig> = {
  active: {
    label: 'Active',
    variant: 'success',
    bgClass: 'bg-emerald-50/70',
    textClass: 'text-emerald-700',
    borderClass: 'border-emerald-200/50',
    dotClass: 'bg-emerald-500',
  },
  pipeline: {
    label: 'Pipeline',
    variant: 'info',
    bgClass: 'bg-blue-50/70',
    textClass: 'text-blue-700',
    borderClass: 'border-blue-200/50',
    dotClass: 'bg-blue-500',
  },
  completed: {
    label: 'Completed',
    variant: 'neutral',
    bgClass: 'bg-slate-100',
    textClass: 'text-slate-700',
    borderClass: 'border-slate-300/40',
    dotClass: 'bg-slate-500',
  },
  on_hold: {
    label: 'On Hold',
    variant: 'warning',
    bgClass: 'bg-amber-50/70',
    textClass: 'text-amber-700',
    borderClass: 'border-amber-200/50',
    dotClass: 'bg-amber-500',
  },
  archived: {
    label: 'Archived',
    variant: 'neutral',
    bgClass: 'bg-slate-100',
    textClass: 'text-slate-500',
    borderClass: 'border-slate-200',
    dotClass: 'bg-slate-400',
  },
};

export const PROPERTY_STATUS_MAP: Record<string, StatusConfig> = {
  listed: {
    label: 'Listed',
    variant: 'success',
    bgClass: 'bg-emerald-50/70',
    textClass: 'text-emerald-700',
    borderClass: 'border-emerald-200/50',
    dotClass: 'bg-emerald-500',
  },
  under_contract: {
    label: 'Under Contract',
    variant: 'warning',
    bgClass: 'bg-amber-50/70',
    textClass: 'text-amber-700',
    borderClass: 'border-amber-200/50',
    dotClass: 'bg-amber-500',
  },
  sold: {
    label: 'Sold',
    variant: 'neutral',
    bgClass: 'bg-slate-100',
    textClass: 'text-slate-700',
    borderClass: 'border-slate-300/40',
    dotClass: 'bg-slate-500',
  },
  leased: {
    label: 'Leased',
    variant: 'info',
    bgClass: 'bg-blue-50/70',
    textClass: 'text-blue-700',
    borderClass: 'border-blue-200/50',
    dotClass: 'bg-blue-500',
  },
  draft: {
    label: 'Draft',
    variant: 'neutral',
    bgClass: 'bg-slate-100',
    textClass: 'text-slate-600',
    borderClass: 'border-slate-200',
    dotClass: 'bg-slate-400',
  },
};

export const WORKFLOW_STATUS_MAP: Record<string, StatusConfig> = {
  pending: {
    label: 'Pending',
    variant: 'neutral',
    bgClass: 'bg-slate-100',
    textClass: 'text-slate-600',
    borderClass: 'border-slate-200',
    dotClass: 'bg-slate-400',
  },
  running: {
    label: 'Running',
    variant: 'primary',
    bgClass: 'bg-indigo-50/70',
    textClass: 'text-indigo-700',
    borderClass: 'border-indigo-200/50',
    dotClass: 'bg-indigo-600 animate-pulse',
  },
  succeeded: {
    label: 'Succeeded',
    variant: 'success',
    bgClass: 'bg-emerald-50/70',
    textClass: 'text-emerald-700',
    borderClass: 'border-emerald-200/50',
    dotClass: 'bg-emerald-500',
  },
  failed: {
    label: 'Failed',
    variant: 'error',
    bgClass: 'bg-rose-50/70',
    textClass: 'text-rose-700',
    borderClass: 'border-rose-200/50',
    dotClass: 'bg-rose-500',
  },
};

/**
 * Gets a unified status configuration for any raw string status
 */
export function getStatusConfig(rawStatus: string | undefined | null, type: 'project' | 'property' | 'workflow'): StatusConfig {
  if (!rawStatus) return DEFAULT_STATUS_CONFIG;
  const normalized = rawStatus.trim().toLowerCase();

  const map = 
    type === 'project' 
      ? PROJECT_STATUS_MAP 
      : type === 'property' 
        ? PROPERTY_STATUS_MAP 
        : WORKFLOW_STATUS_MAP;

  return map[normalized] || {
    ...DEFAULT_STATUS_CONFIG,
    label: rawStatus.charAt(0).toUpperCase() + rawStatus.slice(1),
  };
}
