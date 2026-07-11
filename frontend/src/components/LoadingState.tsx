import { Loader2 } from 'lucide-react';
import styles from './LoadingState.module.css';

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
      <div id={id || 'loading-skeleton'} className={styles.skeletonWrap}>
        <div className={styles.skeletonBlock} />
        <div className={styles.skeletonLines}>
          <div className={styles.skeletonLine} style={{ width: '100%' }} />
          <div className={styles.skeletonLine} style={{ width: '83.33%' }} />
          <div className={styles.skeletonLine} style={{ width: '66.67%' }} />
        </div>
      </div>
    );
  }

  if (type === 'rows') {
    return (
      <div id={id || 'loading-rows'} className={styles.rowsWrap}>
        {Array.from({ length: rowsCount }).map((_, index) => (
          <div key={index} className={`enterprise-card ${styles.rowItem}`}>
            <div className={styles.rowContent}>
              <div className={styles.rowAvatar} />
              <div className={styles.rowLines}>
                <div className={styles.rowLineWide} />
                <div className={styles.rowLineNarrow} />
              </div>
            </div>
          </div>
        ))}
      </div>
    );
  }

  return (
    <div id={id || 'loading-spinner'} className={styles.spinnerWrap}>
      <Loader2 className={styles.spinnerIcon} />
      <p className={styles.spinnerMessage}>{message}</p>
    </div>
  );
}
