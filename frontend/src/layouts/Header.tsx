import React, { useEffect, useState } from 'react';
import { Menu, Bell, Wifi, WifiOff, Loader2 } from 'lucide-react';
import { WimLogicLogo } from './Sidebar';
import { AppConfig } from '../config/app';
import styles from './Header.module.css';

export interface HeaderProps {
  currentView: string;
  onOpenMobile: () => void;
  id?: string;
}

type BackendStatus = 'checking' | 'online' | 'offline';

/**
 * Polls the existing root-level /health endpoint (already present in
 * main.py - no new endpoint invented) to drive the "Backend Linked"
 * indicator. Silently treats any failure (network error, non-2xx) as
 * offline rather than throwing, since this is a passive status indicator.
 */
function useBackendStatus(intervalMs = 30000): BackendStatus {
  const [status, setStatus] = useState<BackendStatus>('checking');

  useEffect(() => {
    let cancelled = false;

    async function checkHealth() {
      try {
        const res = await fetch(`${AppConfig.apiOrigin}/health`);
        if (!cancelled) setStatus(res.ok ? 'online' : 'offline');
      } catch {
        if (!cancelled) setStatus('offline');
      }
    }

    checkHealth();
    const interval = setInterval(checkHealth, intervalMs);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [intervalMs]);

  return status;
}

function useUtcClock(): string {
  const [now, setNow] = useState(() => new Date());

  useEffect(() => {
    const interval = setInterval(() => setNow(new Date()), 30000);
    return () => clearInterval(interval);
  }, []);

  const formatted = now
    .toISOString()
    .slice(0, 16)
    .replace('T', ' ');
  return `${formatted} UTC`;
}

export default function Header({ currentView, onOpenMobile, id }: HeaderProps) {
  const backendStatus = useBackendStatus();
  const utcClock = useUtcClock();

  const statusConfig: Record<BackendStatus, { label: string; className: string; icon: React.ReactNode }> = {
    checking: {
      label: 'Checking...',
      className: styles.statusChecking,
      icon: <Loader2 className="w-3 h-3 animate-spin" />,
    },
    online: {
      label: 'Backend Linked',
      className: styles.statusOnline,
      icon: <Wifi className="w-3 h-3" />,
    },
    offline: {
      label: 'Backend Offline',
      className: styles.statusOffline,
      icon: <WifiOff className="w-3 h-3" />,
    },
  };
  const currentStatus = statusConfig[backendStatus];

  return (
    <header id={id || 'enterprise-header-panel'} className={styles.header}>
      <div className={styles.leftGroup}>
        {/* Mobile menu toggle */}
        <button
          onClick={onOpenMobile}
          className={styles.mobileMenuBtn}
          id="open-sidebar-mobile-btn"
        >
          <Menu className="w-5 h-5" />
        </button>

        {/* Small branding for mobile */}
        <div className={styles.mobileBrand}>
          <WimLogicLogo className="w-5 h-5" />
          <span className={styles.mobileBrandText}>WIMLOGIC</span>
        </div>

        {/* Breadcrumb - desktop only */}
        <div className={styles.breadcrumbArea}>
          <div className={styles.breadcrumbRow}>
            <span>Console</span>
            <span className={styles.breadcrumbSeparator}>/</span>
            <span className={styles.breadcrumbActive}>{currentView}</span>
          </div>
          <span className={styles.pageSubtitle}>AI-CRE ORCHESTRATION CLIENT</span>
        </div>

        {/* Active view name on mobile */}
        <span className={styles.mobileTitle}>{currentView}</span>
      </div>

      <div className={styles.rightGroup}>
        <div className={styles.clockBlock} title="Current UTC time" id="header-utc-clock">
          <span>{utcClock}</span>
        </div>

        <div className={`${styles.statusPill} ${currentStatus.className}`} id="header-backend-status">
          <span className={styles.statusDot} />
          {currentStatus.icon}
          <span className={styles.statusLabel}>{currentStatus.label}</span>
        </div>

        <button className={styles.notifBtn} id="header-notifications-btn" title="Notifications">
          <Bell className="w-4 h-4" />
          <span className={styles.notifDot} />
        </button>
      </div>
    </header>
  );
}
