import { Property } from '../types/index';

export interface PropertySelectorProps {
  properties: Property[];
  selectedPropertyId: number | null;
  onChange: (propertyId: number | null) => void;
  id?: string;
}

/**
 * components/PropertySelector.tsx
 *
 * Home Studio Frontend Checkpoint 2. Plain dropdown bound to the
 * existing propertyService.list() results (owned/fetched by
 * HomeStudio.tsx). Displays a business-friendly address label; the
 * numeric Property database id is preserved as the underlying value,
 * never surfaced to the user.
 */
export default function PropertySelector({ properties, selectedPropertyId, onChange, id }: PropertySelectorProps) {
  return (
    <select
      className="enterprise-form-input"
      value={selectedPropertyId ?? ''}
      onChange={(e) => onChange(e.target.value ? Number(e.target.value) : null)}
      id={id || 'home-studio-property-selector'}
      aria-label="Select a Property"
    >
      <option value="">Select a Property</option>
      {properties.map((p) => (
        <option key={p.id} value={p.id}>
          {p.address || p.property_uid}
        </option>
      ))}
    </select>
  );
}
