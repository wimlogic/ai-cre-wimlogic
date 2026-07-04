import React from 'react';

export interface FormFieldProps {
  children: React.ReactNode;
  label?: string;
  error?: string;
  helpText?: string;
  required?: boolean;
  id?: string;
}

export default function FormField({
  children,
  label,
  error,
  helpText,
  required = false,
  id,
}: FormFieldProps) {
  return (
    <div id={id || 'enterprise-form-field'} className="space-y-1">
      {label && (
        <label className="enterprise-form-label">
          {label}
          {required && <span className="text-rose-500 ml-1 font-bold">*</span>}
        </label>
      )}
      
      <div className="relative">
        {children}
      </div>

      {error ? (
        <p className="enterprise-form-error" role="alert">
          {error}
        </p>
      ) : helpText ? (
        <p className="enterprise-form-help">
          {helpText}
        </p>
      ) : null}
    </div>
  );
}
