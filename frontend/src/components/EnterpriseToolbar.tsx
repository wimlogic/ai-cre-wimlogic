import React from 'react';
import { Search } from 'lucide-react';
import styles from './EnterpriseToolbar.module.css';

export interface EnterpriseToolbarProps {
  searchQuery?: string;
  onSearchChange?: (val: string) => void;
  searchPlaceholder?: string;
  filterContent?: React.ReactNode;
  actionContent?: React.ReactNode;
  id?: string;
}

export default function EnterpriseToolbar({
  searchQuery,
  onSearchChange,
  searchPlaceholder = 'Search records...',
  filterContent,
  actionContent,
  id,
}: EnterpriseToolbarProps) {
  const hasSearch = onSearchChange !== undefined;

  return (
    <div id={id || 'enterprise-toolbar'} className={`enterprise-card ${styles.toolbar}`}>
      <div className={styles.leftGroup}>
        {hasSearch && (
          <div className={styles.searchWrap}>
            <span className={styles.searchIcon}>
              <Search className="w-4 h-4" />
            </span>
            <input
              type="text"
              value={searchQuery || ''}
              onChange={(e) => onSearchChange?.(e.target.value)}
              placeholder={searchPlaceholder}
              className={`enterprise-form-input ${styles.searchInput}`}
              id={id ? `${id}-search` : 'toolbar-search-input'}
            />
          </div>
        )}
        {filterContent && <div className={styles.filterGroup}>{filterContent}</div>}
      </div>

      {actionContent && <div className={styles.actionGroup}>{actionContent}</div>}
    </div>
  );
}
