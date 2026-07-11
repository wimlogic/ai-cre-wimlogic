import React from 'react';
import styles from './EnterpriseCard.module.css';

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
        <div className={styles.header}>
          <div className={styles.headerText}>
            {title && <h3 className={styles.title}>{title}</h3>}
            {subtitle && <p className={styles.subtitle}>{subtitle}</p>}
          </div>
          {headerAction && <div className={styles.headerAction}>{headerAction}</div>}
        </div>
      )}
      <div className={styles.body}>{children}</div>
      {footer && <div className={styles.footer}>{footer}</div>}
    </div>
  );
}
