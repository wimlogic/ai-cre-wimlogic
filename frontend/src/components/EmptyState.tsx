import { LucideIcon, FileX } from 'lucide-react';
import styles from './EmptyState.module.css';

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
    <div id={id || 'enterprise-empty-state'} className={`enterprise-card ${styles.wrapper}`}>
      <div className={styles.iconWrap}>
        <Icon className={styles.icon} />
      </div>
      <h3 className={styles.title}>{title}</h3>
      <p className={styles.description}>{description}</p>
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
