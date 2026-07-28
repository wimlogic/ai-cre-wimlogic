import { useState, ReactNode } from 'react';
import { ChevronRight } from 'lucide-react';
import styles from './ExpandableSection.module.css';

/**
 * components/ExpandableSection.tsx
 *
 * AIHOME Phase 1 (Phase D). The one new structural pattern this phase
 * introduces to the existing Property Image detail modal - per the
 * approved revision, this REPLACES the earlier tab-strip proposal.
 * Sections stack in a single continuous scroll (Details already exists
 * unchanged above these; Versions -> Compare -> Approval render as
 * expandable sections below it, in that fixed order), rather than
 * switching between separate tab panels. No business logic - purely a
 * collapsible container; the caller decides what to render inside and
 * whether/when to lazy-load its data.
 */
export interface ExpandableSectionProps {
  title: string;
  defaultExpanded?: boolean;
  /** Called the first time this section is expanded - the natural place
   * for a caller to lazy-load its own data, so nothing fetches until the
   * user actually opens that section. */
  onFirstExpand?: () => void;
  children: ReactNode;
}

export default function ExpandableSection({ title, defaultExpanded = false, onFirstExpand, children }: ExpandableSectionProps) {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);
  const [hasEverExpanded, setHasEverExpanded] = useState(defaultExpanded);

  const handleToggle = () => {
    const next = !isExpanded;
    setIsExpanded(next);
    if (next && !hasEverExpanded) {
      setHasEverExpanded(true);
      onFirstExpand?.();
    }
  };

  return (
    <div className={styles.section}>
      <button
        type="button"
        className={styles.header}
        onClick={handleToggle}
        aria-expanded={isExpanded}
      >
        <ChevronRight className={`${styles.chevron} ${isExpanded ? styles.chevronExpanded : ''}`} />
        <span className={styles.title}>{title}</span>
      </button>
      {isExpanded && <div className={styles.content}>{children}</div>}
    </div>
  );
}
