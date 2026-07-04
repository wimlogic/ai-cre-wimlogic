import React from 'react';
import { Search } from 'lucide-react';

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
    <div
      id={id || 'enterprise-toolbar'}
      className="flex flex-col md:flex-row md:items-center justify-between gap-4 p-4 enterprise-card bg-white mb-6"
    >
      <div className="flex flex-1 flex-col sm:flex-row items-stretch sm:items-center gap-3">
        {hasSearch && (
          <div className="relative flex-1 max-w-md">
            <span className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
              <Search className="w-4 h-4" />
            </span>
            <input
              type="text"
              value={searchQuery || ''}
              onChange={(e) => onSearchChange?.(e.target.value)}
              placeholder={searchPlaceholder}
              className="enterprise-form-input pl-9"
              id={id ? `${id}-search` : 'toolbar-search-input'}
            />
          </div>
        )}
        {filterContent && (
          <div className="flex items-center gap-2 overflow-x-auto py-0.5 shrink-0">
            {filterContent}
          </div>
        )}
      </div>

      {actionContent && (
        <div className="flex items-center gap-2 shrink-0 md:justify-end">
          {actionContent}
        </div>
      )}
    </div>
  );
}
