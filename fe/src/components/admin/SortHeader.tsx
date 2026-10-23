import type { FC } from 'react';

import type { AdminUserSortEnum } from '@/schemas';
import type { AdminUserSortColumn } from './adminUserFilters';

interface Props {
  column: AdminUserSortColumn;
  label: string;
  sort: AdminUserSortEnum | null;
  onChange: (sort: AdminUserSortEnum | null) => void;
  className?: string;
}

const ICON_PATHS = {
  none: 'M8 9l4-4 4 4M8 15l4 4 4-4',
  asc: 'M12 19V5M5 12l7-7 7 7',
  desc: 'M12 5v14M19 12l-7 7-7-7',
} as const;

const ARIA_SORT = { none: 'none', asc: 'ascending', desc: 'descending' } as const;

/** Column header that cycles unsorted, ascending, descending, unsorted. */
const SortHeader: FC<Props> = ({ column, label, sort, onChange, className = '' }) => {
  const state = sort?.startsWith(`${column}_`) ? (sort.endsWith('_asc') ? 'asc' : 'desc') : 'none';
  const next = state === 'none' ? `${column}_asc` : state === 'asc' ? `${column}_desc` : null;

  return (
    <th aria-sort={ARIA_SORT[state]} className={className}>
      <button
        type="button"
        className="inline-flex items-center gap-1 uppercase tracking-wide hover:text-slate-200"
        onClick={() => onChange(next as AdminUserSortEnum | null)}
      >
        {label}
        <svg
          aria-hidden="true"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth="2.5"
          className={`h-3.5 w-3.5 ${state === 'none' ? 'opacity-40' : 'text-amber-300'}`}
        >
          <path d={ICON_PATHS[state]} />
        </svg>
      </button>
    </th>
  );
};

export default SortHeader;
