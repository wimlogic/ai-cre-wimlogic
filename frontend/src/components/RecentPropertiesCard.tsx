import { useEffect, useState } from 'react';
import { ArrowRight, Image as ImageIcon, Sparkles, Layers } from 'lucide-react';
import EnterpriseCard from './EnterpriseCard';
import LoadingState from './LoadingState';
import { Property, PropertyImage } from '../types/index';
import { propertyService } from '../services/propertyService';
import { propertyImageService } from '../services/propertyImageService';
import { designJobService } from '../services/designJobService';
import { resolveImageSrc } from '../utils/imageUrl';
import { resolvePrimaryPropertyImage } from '../utils/propertyImage';
import styles from './RecentPropertiesCard.module.css';

export interface RecentPropertiesCardProps {
  properties: Property[];
  onNavigate: (view: string) => void;
  onSelectProperty: (id: number | null) => void;
  /**
   * Project business code -> Project Name, built once by Dashboard.tsx
   * from a single Projects fetch. Resolving names here (rather than each
   * card issuing its own Project lookup request) avoids N+1 requests -
   * Checkpoint 2B correction.
   */
  projectLookup: Record<string, string>;
  isLoading: boolean;
}

interface PropertyEnrichment {
  primaryImageSrc: string | null;
  /** The Project's business code (cre_projects.project_id), e.g. "PRJ-7328" - NOT a display name. */
  projectCode: string | null;
  imagesCount: number;
  /**
   * Temporary IMAGE-LEVEL readiness only (true if any of this Property's
   * images has a prompt, tags, constraints, or priority set). This is
   * NOT the full inherited AI readiness that will eventually combine
   * Project Knowledge + Property Knowledge + Image Knowledge + Tool
   * Requirements (Checkpoint 2B correction: do not overstate this as
   * full readiness). Kept as a frontend-only indicator; nothing here is
   * a fabricated backend field.
   */
  aiReady: boolean;
  designCount: number;
}

/**
 * components/RecentPropertiesCard.tsx
 *
 * AI HOME Dashboard - Recent Properties. Replaces the prior Recent
 * Projects card so the Dashboard's first answer is "which properties am
 * I working on today", not a project list.
 *
 * Every field shown is real, sourced from the existing Property Image,
 * Project association, and Design Job APIs - nothing here is fabricated.
 * "AI Ready" is the same frontend-only readiness rule already established
 * for Home Studio (components/ImageKnowledgeSummary.tsx's hasAiKnowledge):
 * true if any of the property's images has a prompt, tags, constraints,
 * or priority set. Design count and images count are real counts from
 * their respective list endpoints, not estimates.
 */
export default function RecentPropertiesCard({ properties, onNavigate, onSelectProperty, projectLookup, isLoading }: RecentPropertiesCardProps) {
  const [enrichment, setEnrichment] = useState<Record<number, PropertyEnrichment>>({});
  const [isEnriching, setIsEnriching] = useState(false);

  useEffect(() => {
    if (properties.length === 0) return;

    let cancelled = false;
    setIsEnriching(true);

    Promise.all(
      properties.map(async (prop) => {
        try {
          const [imagesRes, assocRes, jobsRes] = await Promise.all([
            propertyImageService.list({ property_id: prop.id, include_deleted: false, limit: 100 }),
            propertyService.listAssociations({ property_id: prop.id, limit: 1 }),
            designJobService.list({ property_id: prop.id, limit: 100 }).catch(() => ({ count: 0, items: [] })),
          ]);

          const images = imagesRes.items || [];
          // AI HOME Image Display Standard: primary -> first uploaded ->
          // null (placeholder rendered by this component itself below).
          const primary = resolvePrimaryPropertyImage(images);
          const aiReady = images.some(
            (img: PropertyImage) =>
              Boolean(img.ai_prompt) || (img.tags && img.tags.length > 0) || Boolean(img.constraints) || img.priority != null
          );

          const association = assocRes.items?.[0];
          const projectCode = association ? association.project_id : null;

          return {
            propertyId: prop.id,
            enrichment: {
              primaryImageSrc: primary ? resolveImageSrc(primary) : null,
              projectCode,
              imagesCount: images.length,
              aiReady,
              designCount: jobsRes.count || 0,
            } as PropertyEnrichment,
          };
        } catch (err) {
          console.error(`[Dashboard] Failed to enrich property ${prop.id}:`, err);
          return {
            propertyId: prop.id,
            enrichment: {
              primaryImageSrc: null,
              projectCode: null,
              imagesCount: 0,
              aiReady: false,
              designCount: 0,
            } as PropertyEnrichment,
          };
        }
      })
    ).then((results) => {
      if (cancelled) return;
      const next: Record<number, PropertyEnrichment> = {};
      results.forEach((r) => {
        next[r.propertyId] = r.enrichment;
      });
      setEnrichment(next);
      setIsEnriching(false);
    });

    return () => {
      cancelled = true;
    };
  }, [properties]);

  const handleSelectProperty = (propertyId: number) => {
    onSelectProperty(propertyId);
    onNavigate('Home Studio');
  };

  return (
    <EnterpriseCard
      title="Recent Properties"
      headerAction={
        <button
          onClick={() => onNavigate('Properties')}
          className="text-xs text-indigo-600 hover:text-indigo-800 font-semibold flex items-center gap-1.5 focus:outline-none"
        >
          View All <ArrowRight className="w-3.5 h-3.5" />
        </button>
      }
    >
      {isLoading ? (
        <LoadingState type="rows" rowsCount={3} />
      ) : properties.length === 0 ? (
        <div className="py-12 text-center text-slate-400 text-xs font-mono">NO PROPERTIES YET</div>
      ) : (
        <div className={styles.list}>
          {properties.map((prop) => {
            const info = enrichment[prop.id];
            const resolvedProjectName = info?.projectCode ? projectLookup[info.projectCode] : undefined;
            return (
              <button
                key={prop.id}
                type="button"
                className={styles.propertyRow}
                onClick={() => handleSelectProperty(prop.id)}
              >
                <div className={styles.imageWrap}>
                  {info?.primaryImageSrc ? (
                    <img src={info.primaryImageSrc} alt="" className={styles.image} />
                  ) : (
                    <div className={styles.imagePlaceholder}>
                      <ImageIcon className="w-5 h-5 text-slate-300" />
                    </div>
                  )}
                </div>

                <div className={styles.centerContent}>
                  <div className={styles.addressRow}>
                    <span className={styles.address}>{prop.address || prop.property_uid}</span>
                  </div>
                  <div className={styles.subRow}>
                    {resolvedProjectName ? (
                      <span className={styles.projectChip}>{resolvedProjectName}</span>
                    ) : info?.projectCode ? (
                      // Project record could not be resolved from the lookup -
                      // show the code itself, neutrally labeled, never
                      // presented as if it were the confirmed Project Name.
                      <span className={styles.projectChipUnresolved}>Project {info.projectCode}</span>
                    ) : null}
                    {prop.existing_use && <span className={styles.typeText}>{prop.existing_use}</span>}
                  </div>
                  {!isEnriching && info && (
                    <div className={styles.indicatorRow}>
                      <span className={styles.indicator}>
                        <ImageIcon className="w-3 h-3" />
                        {info.imagesCount} {info.imagesCount === 1 ? 'Photo' : 'Photos'}
                      </span>
                      {info.aiReady && (
                        <span className={`${styles.indicator} ${styles.indicatorGood}`}>
                          <Sparkles className="w-3 h-3" />
                          AI Ready
                        </span>
                      )}
                      {info.designCount > 0 && (
                        <span className={styles.indicator}>
                          <Layers className="w-3 h-3" />
                          {info.designCount} {info.designCount === 1 ? 'Design' : 'Designs'}
                        </span>
                      )}
                    </div>
                  )}
                </div>

                <ArrowRight className={styles.chevron} />
              </button>
            );
          })}
        </div>
      )}
    </EnterpriseCard>
  );
}
