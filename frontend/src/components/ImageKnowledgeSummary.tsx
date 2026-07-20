import { PropertyImage } from '../types/index';
import styles from './ImageKnowledgeSummary.module.css';

export interface ImageKnowledgeSummaryProps {
  image: PropertyImage | null;
  id?: string;
}

/**
 * components/ImageKnowledgeSummary.tsx
 *
 * Home Studio Frontend Checkpoint 2. Frontend-only readiness indicator
 * over the real AI Knowledge fields (ai_prompt, tags, constraints,
 * priority) - never a backend-invented readiness flag. "Available" means
 * at least one of the four fields is populated; "Empty" means none are.
 * This is a compact summary only - the full Image Knowledge editor is
 * explicitly out of scope for this checkpoint.
 */
export function hasAiKnowledge(image: PropertyImage | null | undefined): boolean {
  if (!image) return false;
  return Boolean(
    image.ai_prompt || (image.tags && image.tags.length > 0) || image.constraints || image.priority != null
  );
}

export default function ImageKnowledgeSummary({ image, id }: ImageKnowledgeSummaryProps) {
  if (!image) return null;

  const tagsCount = image.tags?.length || 0;

  return (
    <div className={styles.wrapper} id={id || 'image-knowledge-summary'}>
      <span className={styles.heading}>AI Knowledge</span>
      <div className={styles.row}>
        <span className={styles.label}>Prompt</span>
        <span className={image.ai_prompt ? styles.valuePresent : styles.valueMissing}>
          {image.ai_prompt ? 'Available' : 'Not set'}
        </span>
      </div>
      <div className={styles.row}>
        <span className={styles.label}>Tags</span>
        <span className={tagsCount > 0 ? styles.valuePresent : styles.valueMissing}>
          {tagsCount > 0 ? `${tagsCount} tag${tagsCount === 1 ? '' : 's'}` : 'None'}
        </span>
      </div>
      <div className={styles.row}>
        <span className={styles.label}>Constraints</span>
        <span className={image.constraints ? styles.valuePresent : styles.valueMissing}>
          {image.constraints ? 'Available' : 'Not set'}
        </span>
      </div>
      <div className={styles.row}>
        <span className={styles.label}>Priority</span>
        <span className={image.priority != null ? styles.valuePresent : styles.valueMissing}>
          {image.priority != null ? image.priority : 'Not set'}
        </span>
      </div>
    </div>
  );
}
