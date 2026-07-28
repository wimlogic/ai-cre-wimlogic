import { X } from 'lucide-react';

export interface DesignJobFlowModalProps {
  isOpen: boolean;
  onClose: () => void;
  children: React.ReactNode;
}

/**
 * components/DesignJobFlowModal.tsx
 *
 * AIHOME Design Studio V2 - Design Job User Experience. Shared dialog
 * shell for the Progress and Results phases of the Generate flow,
 * matching DesignJobWorkspace's own overlay/panel styling exactly so the
 * handoff from Workspace -> Progress -> Results reads as one continuous
 * experience rather than a jarring switch between differently-styled
 * popups, even though each phase is technically a separate modal
 * instance rather than one component with internal view-switching.
 */
export default function DesignJobFlowModal({ isOpen, onClose, children }: DesignJobFlowModalProps) {
  if (!isOpen) return null;

  return (
    <div className="enterprise-dialog-overlay" onClick={onClose} id="design-job-flow-overlay">
      <div
        className="enterprise-dialog-panel"
        style={{ width: 'min(40rem, 92vw)', maxHeight: '90vh', overflowY: 'auto' }}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="enterprise-dialog-header">
          <div />
          <button type="button" onClick={onClose} aria-label="Close" style={{ background: 'none', border: 'none', cursor: 'pointer' }}>
            <X className="w-4 h-4" />
          </button>
        </div>
        <div className="enterprise-dialog-body">{children}</div>
      </div>
    </div>
  );
}
