import { type ReactNode } from 'react';

interface FieldProps {
  label: string;
  htmlFor: string;
  error?: string | undefined;
  hint?: string;
  children: ReactNode;
}

const Field = ({ label, htmlFor, error, hint, children }: FieldProps) => (
  <div className="space-y-1">
    <label htmlFor={htmlFor} className="block text-sm font-medium text-slate-200">
      {label}
    </label>
    {children}
    {error ? (
      <p className="text-xs text-rose-400" role="alert">
        {error}
      </p>
    ) : hint ? (
      <p className="text-xs text-slate-500">{hint}</p>
    ) : null}
  </div>
);

export default Field;
