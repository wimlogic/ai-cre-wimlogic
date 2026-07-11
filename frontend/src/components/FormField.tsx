import React from 'react';
import styles from './FormField.module.css';

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
    <div id={id || 'enterprise-form-field'} className={styles.field}>
      {label && (
        <label className="enterprise-form-label">
          {label}
          {required && <span className="enterprise-form-required">*</span>}
        </label>
      )}

      <div className={styles.controlWrap}>{children}</div>

      {error ? (
        <p className="enterprise-form-error" role="alert">
          {error}
        </p>
      ) : helpText ? (
        <p className="enterprise-form-help">{helpText}</p>
      ) : null}
    </div>
  );
}
