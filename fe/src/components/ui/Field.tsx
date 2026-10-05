import { type ReactNode } from 'react';

import HelpTip from './HelpTip';

interface FieldProps {
  label: string;
  htmlFor: string;
  error?: string | undefined;
  hint?: string;
  help?: string;
  children: ReactNode;
}

const Field = ({ label, htmlFor, error, hint, help, children }: FieldProps) => (
  <div className="space-y-1">
    <div className="flex items-center gap-1.5">
      <label htmlFor={htmlFor} className="block text-sm font-medium text-slate-200">
        {label}
      </label>
      {help ? <HelpTip text={help} /> : null}
    </div>
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
