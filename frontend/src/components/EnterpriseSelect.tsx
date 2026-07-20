export interface EnterpriseSelectOption {
  value: string;
  label: string;
}

export interface EnterpriseSelectProps {
  value: string;
  options: EnterpriseSelectOption[];
  onChange: (value: string) => void;
  placeholder?: string;
  id?: string;
  disabled?: boolean;
}

/**
 * components/EnterpriseSelect.tsx
 *
 * Generic controlled dropdown, built on the project's existing
 * `.enterprise-form-input` styling (the same class PropertySelector.tsx
 * already applies to a native <select> - this project's established
 * "standardized dropdown" convention, not a separate component library).
 *
 * Safely handles values outside the approved option list (older or
 * unexpected backend data) by rendering them as a distinct,
 * clearly-labeled "Unknown: {value}" option rather than silently
 * dropping or replacing them - the raw value is preserved exactly as
 * stored until the user actively picks a real option and saves.
 */
export default function EnterpriseSelect({ value, options, onChange, placeholder, id, disabled }: EnterpriseSelectProps) {
  const isKnownValue = value === '' || options.some((opt) => opt.value === value);

  return (
    <select
      className="enterprise-form-input"
      value={value}
      onChange={(e) => onChange(e.target.value)}
      id={id}
      disabled={disabled}
    >
      {placeholder && <option value="">{placeholder}</option>}
      {!isKnownValue && <option value={value}>Unknown: {value}</option>}
      {options.map((opt) => (
        <option key={opt.value} value={opt.value}>
          {opt.label}
        </option>
      ))}
    </select>
  );
}
