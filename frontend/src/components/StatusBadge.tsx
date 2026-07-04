import React from 'react';
import { getStatusConfig } from '../utils/status';

export interface StatusBadgeProps {
  status: string | undefined | null;
  type: 'project' | 'property' | 'workflow';
  id?: string;
}

export default function StatusBadge({ status, type, id }: StatusBadgeProps) {
  const config = getStatusConfig(status, type);

  return (
    <span
      id={id || `status-badge-${status}-${type}`}
      className={`
        enterprise-badge
        ${config.bgClass}
        ${config.textClass}
        ${config.borderClass}
      `}
    >
      <span className={`w-1.5 h-1.5 rounded-full ${config.dotClass}`} />
      <span>{config.label}</span>
    </span>
  );
}
