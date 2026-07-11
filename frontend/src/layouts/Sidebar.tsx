import React from 'react';
import {
  LayoutDashboard,
  FolderOpen,
  Building2,
  Camera,
  Cpu,
  ClipboardList,
  FileCheck,
  Settings as SettingsIcon,
  ChevronRight,
  X,
  User,
} from 'lucide-react';
import { AppConfig } from '../config/app';
import styles from './Sidebar.module.css';

// Customized high-fidelity SVG icon for the WIMLOGIC brand logo (recreated from the uploaded design)
export function WimLogicLogo({ className = 'w-8 h-8' }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 100 100"
      className={className}
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      id="wimlogic-brand-logo"
    >
      <defs>
        {/* Teal ribbon gradient */}
        <linearGradient id="wimTealGrad" x1="0" y1="0" x2="100" y2="100">
          <stop offset="0%" stopColor="#81b29a" />
          <stop offset="50%" stopColor="#3d5a80" />
          <stop offset="100%" stopColor="#293241" />
        </linearGradient>
        {/* Shimmer gradient for 3D ribbon look */}
        <linearGradient id="wimTealShine" x1="0" y1="0" x2="0" y2="100">
          <stop offset="0%" stopColor="#80ced7" />
          <stop offset="60%" stopColor="#4895ef" />
          <stop offset="100%" stopColor="#3f37c9" />
        </linearGradient>
        {/* Central orange pillar gradient */}
        <linearGradient id="wimOrangeGrad" x1="0" y1="0" x2="0" y2="100">
          <stop offset="0%" stopColor="#ffb703" />
          <stop offset="100%" stopColor="#fb8500" />
        </linearGradient>
      </defs>

      {/* Left wave/ribbon (representing 'W') */}
      <path
        d="M 12 55 C 8 38, 22 36, 26 50 C 31 66, 38 82, 44 86 C 41 72, 28 42, 24 44 C 18 47, 10 50, 10 54"
        fill="url(#wimTealShine)"
        opacity="0.9"
      />
      <path
        d="M 10 52 C 10 40, 20 40, 26 55 C 32 70, 42 75, 46 80 L 46 86 C 36 84, 25 65, 18 58 C 14 54, 10 53, 10 52 Z"
        fill="url(#wimTealGrad)"
      />

      {/* Central Orange Pillar (representing 'I' / Person) */}
      {/* Pillar body */}
      <rect
        x="43"
        y="23"
        width="10"
        height="64"
        rx="5"
        fill="url(#wimOrangeGrad)"
      />
      {/* Pillar top circular dot/head */}
      <circle
        cx="48"
        cy="13"
        r="5.5"
        fill="url(#wimOrangeGrad)"
      />

      {/* Right wave/ribbon (representing 'M') */}
      <path
        d="M 52 28 C 54 36, 62 60, 68 76 C 74 60, 84 32, 90 32 C 94 32, 92 46, 88 56 C 82 72, 74 78, 66 78 C 58 78, 54 50, 52 28 Z"
        fill="url(#wimTealGrad)"
      />
      <path
        d="M 52 28 C 53 45, 62 76, 67 78 C 65 72, 59 40, 53 30 C 52 29, 52 28, 52 28 Z"
        fill="url(#wimTealShine)"
        opacity="0.8"
      />

      {/* Trademark "tm" text symbol */}
      <text
        x="90"
        y="12"
        fill="#3d5a80"
        fontSize="8"
        fontWeight="bold"
        fontFamily="sans-serif"
      >
        tm
      </text>
    </svg>
  );
}

export interface SidebarProps {
  currentView: string;
  onNavigate: (view: string) => void;
  selectedProjectId?: string;
  isMobileOpen: boolean;
  onCloseMobile: () => void;
}

interface NavItem {
  id: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
}

interface NavGroup {
  label: string;
  items: NavItem[];
}

// Same routes/view identifiers as before - grouped only for visual hierarchy.
// No navigation targets added, removed, or renamed.
const NAV_GROUPS: NavGroup[] = [
  {
    label: 'Overview',
    items: [{ id: 'Dashboard', label: 'Dashboard', icon: LayoutDashboard }],
  },
  {
    label: 'Workspace',
    items: [
      { id: 'Projects', label: 'Projects', icon: FolderOpen },
      { id: 'Properties', label: 'Properties', icon: Building2 },
      { id: 'Property Images', label: 'Property Images', icon: Camera },
    ],
  },
  {
    label: 'AI Operations',
    items: [
      { id: 'AI Orchestration', label: 'AI Orchestration', icon: Cpu },
      { id: 'Workflow Results', label: 'Workflow Results', icon: ClipboardList },
      { id: 'Generated Assets', label: 'Generated Assets', icon: FileCheck },
    ],
  },
  {
    label: 'Platform',
    items: [{ id: 'Settings', label: 'Settings', icon: SettingsIcon }],
  },
];

// Personalized identity, unchanged from what previously lived in Header.tsx -
// simply relocated to the sidebar footer to match the WIMLOGIC Enterprise UX
// reference (DEV-TOOLS pins user identity at the bottom of the sidebar).
const CURRENT_USER = {
  name: 'Tim G.',
  email: 'timg@kshoesusa.com',
};

export default function Sidebar({
  currentView,
  onNavigate,
  selectedProjectId,
  isMobileOpen,
  onCloseMobile,
}: SidebarProps) {
  return (
    <>
      <aside
        id="enterprise-sidebar-panel"
        className={`${styles.sidebar} ${isMobileOpen ? styles.sidebarOpen : ''}`}
      >
        <div className={styles.topSection}>
          {/* Logo & Header */}
          <div className={styles.brandRow}>
            <div className={styles.brandGroup}>
              <div className={styles.brandIconWrap}>
                <WimLogicLogo className="w-7 h-7" />
              </div>
              <div>
                <span className={styles.brandName}>WIMLOGIC</span>
                <span className={styles.brandSubtitle}>AI-CRE PLATFORM</span>
              </div>
            </div>
            <button
              onClick={onCloseMobile}
              className={styles.closeMobileBtn}
              id="close-sidebar-mobile-btn"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Navigation Links, grouped for information hierarchy */}
          <nav id="sidebar-navigation" style={{ display: 'flex', flexDirection: 'column', gap: '1.125rem' }}>
            {NAV_GROUPS.map((group) => (
              <div key={group.label} className={styles.navGroup}>
                <span className={styles.navGroupLabel}>{group.label}</span>
                {group.items.map((item) => {
                  const isActive = currentView === item.id;
                  const IconComponent = item.icon;
                  return (
                    <button
                      key={item.id}
                      onClick={() => {
                        onNavigate(item.id);
                        onCloseMobile();
                      }}
                      id={`sidebar-nav-${item.id.toLowerCase().replace(/\s+/g, '-')}`}
                      className={`${styles.navButton} ${isActive ? styles.navButtonActive : ''}`}
                    >
                      <div className={styles.navButtonContent}>
                        <IconComponent className={styles.navIcon} />
                        <span>{item.label}</span>
                      </div>
                      {isActive && <ChevronRight className={styles.navChevron} />}
                    </button>
                  );
                })}
              </div>
            ))}
          </nav>
        </div>

        {/* Sidebar Footer: active project context + user identity + version */}
        <div className={styles.footerSection}>
          {selectedProjectId && (
            <div className={styles.activeProjectCard} id="sidebar-active-project">
              <span className={styles.activeProjectLabel}>Active Project</span>
              <span className={styles.activeProjectValue}>{selectedProjectId}</span>
            </div>
          )}

          <div className={styles.userCard} id="sidebar-user-identity">
            <div className={styles.userAvatar}>
              <User className="w-4 h-4" />
            </div>
            <div className={styles.userTextGroup}>
              <span className={styles.userName}>{CURRENT_USER.name}</span>
              <span className={styles.userEmail}>{CURRENT_USER.email}</span>
            </div>
          </div>

          <div className={styles.versionTag}>
            v{AppConfig.version || '1.0.0'} &bull; Client Handshake
          </div>
        </div>
      </aside>

      {/* Backdrop for Mobile Drawer */}
      {isMobileOpen && (
        <div
          id="sidebar-mobile-backdrop"
          onClick={onCloseMobile}
          className={styles.backdrop}
        ></div>
      )}
    </>
  );
}
