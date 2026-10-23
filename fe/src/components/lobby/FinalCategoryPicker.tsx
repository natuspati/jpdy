import { useState } from 'react';

import Input from '@/components/ui/Input';
import type { PromptCategoryWithPrompts } from '@/schemas';
import { formatLocalDateTime } from '@/utils/formatDateTime';

interface Props {
  id: string;
  categories: PromptCategoryWithPrompts[];
  value: number | null;
  disabled?: boolean;
  onChange: (id: number | null) => void;
}

const optionClass = (selected: boolean) =>
  `flex w-full items-center justify-between gap-2 px-3 py-2 text-left text-sm hover:bg-slate-800 ${
    selected ? 'bg-slate-800 text-amber-300' : 'text-slate-100'
  }`;

/** Searchable single-select; options keep the order they are given (own first, newest first). */
const FinalCategoryPicker = ({ id, categories, value, disabled, onChange }: Props) => {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState('');
  const selected = categories.find((category) => category.id === value);
  const needle = search.trim().toLowerCase();
  const visible = categories.filter((category) => category.name.toLowerCase().includes(needle));

  const choose = (categoryId: number | null) => {
    onChange(categoryId);
    setOpen(false);
    setSearch('');
  };

  return (
    <div className="space-y-2">
      <button
        id={id}
        type="button"
        aria-haspopup="listbox"
        aria-expanded={open}
        disabled={disabled}
        onClick={() => setOpen((prev) => !prev)}
        className="flex h-11 w-full items-center justify-between gap-2 rounded-md border border-slate-700 bg-slate-950 px-3 text-left text-slate-100 disabled:cursor-not-allowed disabled:opacity-50"
      >
        <span className="truncate">{selected ? selected.name : 'No final'}</span>
        <span aria-hidden="true" className="text-slate-400">
          {open ? '▴' : '▾'}
        </span>
      </button>
      {open ? (
        <div className="space-y-2 rounded-md border border-slate-700 bg-slate-950 p-2">
          <Input
            type="search"
            aria-label="Search final categories"
            placeholder="Search final categories"
            autoFocus
            value={search}
            onChange={(event) => setSearch(event.target.value)}
          />
          <div role="listbox" className="max-h-56 overflow-y-auto rounded-md">
            <button
              type="button"
              role="option"
              aria-selected={value === null}
              className={optionClass(value === null)}
              onClick={() => choose(null)}
            >
              No final
            </button>
            {visible.map((category) => (
              <button
                key={category.id}
                type="button"
                role="option"
                aria-selected={category.id === value}
                className={optionClass(category.id === value)}
                onClick={() => choose(category.id)}
              >
                <span className="truncate">{category.name}</span>
                <span className="shrink-0 text-xs text-slate-400">
                  Updated {formatLocalDateTime(category.updated_at)}
                </span>
              </button>
            ))}
            {visible.length === 0 ? (
              <p className="px-3 py-2 text-sm text-slate-400">No final categories match.</p>
            ) : null}
          </div>
        </div>
      ) : null}
    </div>
  );
};

export default FinalCategoryPicker;
