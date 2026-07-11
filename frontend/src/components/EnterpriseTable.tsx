import React, { useState } from 'react';
import LoadingState from './LoadingState';
import EmptyState from './EmptyState';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import styles from './EnterpriseTable.module.css';

export interface ColumnDefinition<T> {
  key: string;
  header: string;
  render?: (row: T) => React.ReactNode;
  width?: string;
  align?: 'left' | 'right' | 'center';
}

export interface EnterpriseTableProps<T> {
  columns: ColumnDefinition<T>[];
  data: T[] | undefined | null;
  rowKeyField: keyof T;
  isLoading?: boolean;
  onRowClick?: (row: T) => void;
  emptyTitle?: string;
  emptyDescription?: string;
  itemsPerPage?: number;
  id?: string;
}

export default function EnterpriseTable<T>({
  columns,
  data,
  rowKeyField,
  isLoading = false,
  onRowClick,
  emptyTitle = 'No records found',
  emptyDescription = 'There are no items currently available in this dataset.',
  itemsPerPage = 10,
  id,
}: EnterpriseTableProps<T>) {
  const [currentPage, setCurrentPage] = useState(1);

  if (isLoading) {
    return <LoadingState type="rows" rowsCount={5} id={id ? `${id}-loading` : 'table-loading'} />;
  }

  const dataset = data || [];

  if (dataset.length === 0) {
    return (
      <EmptyState
        id={id ? `${id}-empty` : 'table-empty'}
        title={emptyTitle}
        description={emptyDescription}
      />
    );
  }

  // Pagination calculations
  const totalItems = dataset.length;
  const totalPages = Math.ceil(totalItems / itemsPerPage);
  const startIndex = (currentPage - 1) * itemsPerPage;
  const paginatedData = dataset.slice(startIndex, startIndex + itemsPerPage);

  const handlePrevPage = () => {
    if (currentPage > 1) setCurrentPage(currentPage - 1);
  };

  const handleNextPage = () => {
    if (currentPage < totalPages) setCurrentPage(currentPage + 1);
  };

  return (
    <div id={id || 'enterprise-table-wrapper'} className={styles.wrapper}>
      <div className="enterprise-table-container">
        <table className="enterprise-table">
          <thead className="enterprise-table-thead">
            <tr>
              {columns.map((col, idx) => (
                <th
                  key={`${col.key}-${idx}`}
                  style={{ width: col.width, textAlign: col.align || 'left' }}
                  className="enterprise-table-th"
                >
                  {col.header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="enterprise-table-tbody">
            {paginatedData.map((row, rowIdx) => (
              <tr
                key={String(row[rowKeyField]) || String(rowIdx)}
                onClick={() => onRowClick?.(row)}
                className={`enterprise-table-tr ${onRowClick ? styles.rowClickable : ''}`}
              >
                {columns.map((col, colIdx) => (
                  <td
                    key={`${col.key}-${colIdx}`}
                    style={{ textAlign: col.align || 'left' }}
                    className="enterprise-table-td"
                  >
                    {col.render ? col.render(row) : String(row[col.key as keyof T] ?? '—')}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {totalPages > 1 && (
        <div className={styles.paginationBar}>
          <span className={styles.paginationInfo}>
            SHOWING {startIndex + 1} - {Math.min(startIndex + itemsPerPage, totalItems)} OF {totalItems}
          </span>
          <div className={styles.paginationControls}>
            <button onClick={handlePrevPage} disabled={currentPage === 1} className={styles.pageBtn}>
              <ChevronLeft className="w-4 h-4" />
            </button>
            <span className={styles.pageLabel}>
              PAGE {currentPage} OF {totalPages}
            </span>
            <button
              onClick={handleNextPage}
              disabled={currentPage === totalPages}
              className={styles.pageBtn}
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
