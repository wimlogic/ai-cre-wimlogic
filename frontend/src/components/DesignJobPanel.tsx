import EnterpriseSelect from './EnterpriseSelect';
import { DesignTool, DesignToolOption } from '../types/index';
import styles from './DesignJobPanel.module.css';

export interface DesignJobPanelProps {
  selectedOriginalCount: number;
  selectedVersionCount: number;
  instruction: string;
  onInstructionChange: (value: string) => void;
  tools: DesignTool[];
  selectedToolId: number | null;
  onSelectTool: (toolId: number | null) => void;
  toolOptions: DesignToolOption[];
  toolOptionValues: Record<string, any>;
  onToolOptionChange: (optionCode: string, value: any) => void;
  /** AIHOME Design Studio V2 - a clear, pre-submit message when the
   * current image selection doesn't fit this Tool's Image Requirements
   * (e.g. too many images for a single-image Tool) - shown instead of
   * letting Generate fail after a round trip to the backend. */
  imageRoleError: string | null;
  onGenerate: () => void;
  isSubmitting: boolean;
  id?: string;
}

/**
 * components/DesignJobPanel.tsx
 *
 * AIHOME Design Studio V2 - Image Workspace Evolution. Right panel of
 * the Design Job Workspace: what's selected, a brand-new instruction
 * (never inherited, never merged from a prior job - the textarea always
 * starts empty for every new workspace session), which Design Tool to
 * run, and Generate.
 *
 * "Workflow" per the approved layout is deliberately NOT rendered as its
 * own separate field - workflow_code is internal-only, never shown to
 * the user anywhere else in this codebase (DesignTool.workflow_code is
 * explicitly commented "never rendered in Home Studio" on the type
 * itself); the Tool the user picks IS the business-facing equivalent of
 * "which workflow", so showing both would either duplicate the same
 * information or leak an internal identifier.
 */
export default function DesignJobPanel({
  selectedOriginalCount,
  selectedVersionCount,
  instruction,
  onInstructionChange,
  tools,
  selectedToolId,
  onSelectTool,
  toolOptions,
  toolOptionValues,
  onToolOptionChange,
  imageRoleError,
  onGenerate,
  isSubmitting,
  id,
}: DesignJobPanelProps) {
  const totalSelected = selectedOriginalCount + selectedVersionCount;

  // Required Tool Options with no value yet (and no default already
  // seeded) block Generate - this is exactly the same rule
  // _resolve_tool_options() enforces server-side; checking it here
  // means the user sees WHY nothing happened instead of a silent
  // failure or a generic error after the fact.
  const missingRequiredOptions = toolOptions.filter(
    (opt) => opt.is_required === 1 && (toolOptionValues[opt.option_code] === undefined || toolOptionValues[opt.option_code] === '')
  );

  const canGenerate =
    totalSelected > 0 &&
    instruction.trim().length > 0 &&
    selectedToolId !== null &&
    missingRequiredOptions.length === 0 &&
    !imageRoleError &&
    !isSubmitting;

  const toolSelectOptions = tools.map((tool) => ({ value: String(tool.id), label: tool.tool_name }));

  return (
    <div className={styles.panel} id={id || 'design-job-panel'}>
      <div className={styles.section}>
        <span className={styles.label}>Selected Images</span>
        <div className={styles.selectionSummary}>
          <span className={styles.summaryChip}>{selectedOriginalCount} Original</span>
          <span className={styles.summaryChip}>{selectedVersionCount} AI Generated</span>
        </div>
        {totalSelected === 0 && <p className={styles.hintText}>Select images from the library to include them.</p>}
        {imageRoleError && <p className={styles.optionWarning}>{imageRoleError}</p>}
      </div>

      <div className={styles.section}>
        <span className={styles.label}>New Instruction</span>
        <textarea
          className={`enterprise-form-input ${styles.instructionInput}`}
          placeholder="Describe what this Design Job should do, e.g. 'Keep the kitchen layout but create a luxury contemporary version with marble countertops.'"
          value={instruction}
          onChange={(e) => onInstructionChange(e.target.value)}
          rows={6}
          id="design-job-instruction-input"
        />
        <p className={styles.hintText}>Every Design Job starts with a brand-new instruction - nothing is carried over automatically.</p>
      </div>

      <div className={styles.section}>
        <span className={styles.label}>Design Tool</span>
        <EnterpriseSelect
          value={selectedToolId !== null ? String(selectedToolId) : ''}
          options={toolSelectOptions}
          onChange={(v) => onSelectTool(v ? Number(v) : null)}
          placeholder="Select a Design Tool"
          id="design-job-tool-select"
        />
      </div>

      {toolOptions.length > 0 && (
        <div className={styles.section}>
          <span className={styles.label}>Tool Options</span>
          {toolOptions.map((opt) => {
            const value = toolOptionValues[opt.option_code];
            if (opt.option_type === 'boolean') {
              return (
                <label key={opt.id} className={styles.optionCheckboxRow}>
                  <input
                    type="checkbox"
                    checked={!!value}
                    onChange={(e) => onToolOptionChange(opt.option_code, e.target.checked)}
                  />
                  {opt.option_label}{opt.is_required === 1 && ' *'}
                </label>
              );
            }
            if (opt.option_type === 'select' && Array.isArray(opt.allowed_values_json)) {
              return (
                <div key={opt.id} className={styles.optionField}>
                  <span className={styles.optionLabel}>{opt.option_label}{opt.is_required === 1 && ' *'}</span>
                  <EnterpriseSelect
                    value={value !== undefined ? String(value) : ''}
                    options={opt.allowed_values_json.map((v) => ({ value: String(v), label: String(v) }))}
                    onChange={(v) => onToolOptionChange(opt.option_code, v)}
                    placeholder={`Select ${opt.option_label}`}
                    id={`design-job-option-${opt.option_code}`}
                  />
                </div>
              );
            }
            return (
              <div key={opt.id} className={styles.optionField}>
                <span className={styles.optionLabel}>{opt.option_label}{opt.is_required === 1 && ' *'}</span>
                <input
                  type={opt.option_type === 'number' ? 'number' : 'text'}
                  className="enterprise-form-input"
                  value={value ?? ''}
                  onChange={(e) => onToolOptionChange(opt.option_code, opt.option_type === 'number' ? Number(e.target.value) : e.target.value)}
                  id={`design-job-option-${opt.option_code}`}
                />
              </div>
            );
          })}
          {missingRequiredOptions.length > 0 && (
            <p className={styles.optionWarning}>
              Required: {missingRequiredOptions.map((o) => o.option_label).join(', ')}
            </p>
          )}
        </div>
      )}

      <button
        type="button"
        className="enterprise-btn enterprise-btn-primary"
        onClick={onGenerate}
        disabled={!canGenerate}
        id="design-job-generate-btn"
      >
        {isSubmitting ? 'Submitting...' : 'Generate'}
      </button>
    </div>
  );
}
