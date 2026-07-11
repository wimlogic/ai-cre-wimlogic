import { getStatusConfig } from '../utils/status';
import styles from './StatusBadge.module.css';

export interface StatusBadgeProps {
  status: string | undefined | null;
  type: 'project' | 'property' | 'workflow';
  id?: string;
}

const VARIANT_CLASS: Record<string, string> = {
  success: styles.success,
  warning: styles.warning,
  error: styles.error,
  info: styles.info,
  primary: styles.primary,
  neutral: styles.neutral,
};

export default function StatusBadge({ status, type, id }: StatusBadgeProps) {
  const config = getStatusConfig(status, type);
  const variantClass = VARIANT_CLASS[config.variant] || styles.neutral;

  return (
    <span
      id={id || `status-badge-${status}-${type}`}
      className={`enterprise-badge ${variantClass}`}
    >
      <span className={styles.dot} />
      <span>{config.label}</span>
    </span>
  );
}
