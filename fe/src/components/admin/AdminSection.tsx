import { type ReactNode } from 'react';

interface Props {
  title: string;
  actions?: ReactNode;
  children: ReactNode;
}

/** A titled admin panel. On `lg` it fills its grid cell and scrolls inside; below, it caps its height. */
const AdminSection = ({ title, actions, children }: Props) => (
  <section className="flex min-h-0 min-w-0 flex-col gap-3">
    <div className="flex flex-wrap items-center justify-between gap-2">
      <h2 className="text-lg font-semibold text-slate-100">{title}</h2>
      {actions}
    </div>
    <div className="max-h-[28rem] min-h-0 overflow-auto rounded-lg border border-slate-800 lg:max-h-none lg:flex-1">
      {children}
    </div>
  </section>
);

export default AdminSection;
