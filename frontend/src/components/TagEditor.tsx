import { useState, KeyboardEvent } from 'react';
import { X } from 'lucide-react';
import styles from './TagEditor.module.css';

export interface TagEditorProps {
  tags: string[];
  onChange: (tags: string[]) => void;
  disabled?: boolean;
  id?: string;
}

/**
 * components/TagEditor.tsx
 *
 * Simple chip-based tag editor. No dedicated tag-input component existed
 * anywhere in the codebase prior to this (confirmed by audit), so this
 * is a small, new, reusable one rather than a one-off inline control.
 * Supports comma-separated entry (typing "brick, roof," adds both
 * "brick" and "roof" immediately) as well as pressing Enter for a
 * single tag, per the task's explicit fallback instruction. Duplicate
 * and blank tags are silently ignored rather than erroring.
 */
export default function TagEditor({ tags, onChange, disabled, id }: TagEditorProps) {
  const [draft, setDraft] = useState('');

  const commitDraft = (raw: string) => {
    const pieces = raw
      .split(',')
      .map((t) => t.trim())
      .filter((t) => t.length > 0);
    if (pieces.length === 0) return;
    const next = [...tags];
    pieces.forEach((tag) => {
      if (!next.includes(tag)) next.push(tag);
    });
    onChange(next);
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' || e.key === ',') {
      e.preventDefault();
      if (draft.trim()) {
        commitDraft(draft);
        setDraft('');
      }
    } else if (e.key === 'Backspace' && draft === '' && tags.length > 0) {
      onChange(tags.slice(0, -1));
    }
  };

  const removeTag = (tag: string) => {
    onChange(tags.filter((t) => t !== tag));
  };

  return (
    <div className={styles.wrapper} id={id}>
      <div className={styles.chipRow}>
        {tags.map((tag) => (
          <span key={tag} className={styles.chip}>
            {tag}
            {!disabled && (
              <button type="button" className={styles.removeBtn} onClick={() => removeTag(tag)} aria-label={`Remove tag ${tag}`}>
                <X className="w-3 h-3" />
              </button>
            )}
          </span>
        ))}
      </div>
      {!disabled && (
        <input
          type="text"
          className="enterprise-form-input"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Add tags, comma-separated (e.g. exterior, brick)"
        />
      )}
    </div>
  );
}
