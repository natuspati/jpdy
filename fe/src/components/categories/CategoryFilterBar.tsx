import { type FC, useState } from 'react';

import Button from '@/components/ui/Button';
import FilterSelect from '@/components/ui/FilterSelect';
import Input from '@/components/ui/Input';
import Modal from '@/components/ui/Modal';
import { type CategoryListFilters, activeFilterCount } from './categoryFilters';

interface Props {
  value: CategoryListFilters;
  onChange: (value: CategoryListFilters) => void;
}

const READINESS_OPTIONS = [
  { value: 'all', label: 'All' },
  { value: 'complete', label: 'Complete' },
  { value: 'incomplete', label: 'Incomplete' },
] as const satisfies ReadonlyArray<{ value: CategoryListFilters['readiness']; label: string }>;

const KIND_OPTIONS = [
  { value: 'all', label: 'All' },
  { value: 'standard', label: 'Standard' },
  { value: 'final', label: 'Final' },
] as const satisfies ReadonlyArray<{ value: CategoryListFilters['kind']; label: string }>;

const SORT_OPTIONS = [
  { value: 'updated_desc', label: 'Newest' },
  { value: 'updated_asc', label: 'Oldest' },
  { value: 'name_asc', label: 'A-Z' },
  { value: 'name_desc', label: 'Z-A' },
] as const satisfies ReadonlyArray<{ value: CategoryListFilters['sort']; label: string }>;

const FilterSelects: FC<Props & { className: string }> = ({ value, onChange, className }) => (
  <div className={className}>
    <FilterSelect
      label="Completeness"
      value={value.readiness}
      options={READINESS_OPTIONS}
      onChange={(readiness) => onChange({ ...value, readiness })}
    />
    <FilterSelect
      label="Type"
      value={value.kind}
      options={KIND_OPTIONS}
      onChange={(kind) => onChange({ ...value, kind })}
    />
    <FilterSelect
      label="Sort"
      value={value.sort}
      options={SORT_OPTIONS}
      onChange={(sort) => onChange({ ...value, sort })}
    />
  </div>
);

/** Filters, sort and search for the category list. On mobile the selects open in a bottom sheet. */
const CategoryFilterBar: FC<Props> = ({ value, onChange }) => {
  const [sheetOpen, setSheetOpen] = useState(false);
  const activeCount = activeFilterCount(value);

  return (
    <div className="flex w-full flex-wrap items-center gap-2 sm:w-auto sm:justify-end">
      <Input
        type="search"
        aria-label="Search categories"
        placeholder="Search categories"
        className="h-9 w-full py-1 sm:order-2 sm:w-56"
        value={value.search}
        onChange={(event) => onChange({ ...value, search: event.target.value })}
      />
      <Button
        type="button"
        size="sm"
        variant="secondary"
        className="sm:hidden"
        onClick={() => setSheetOpen(true)}
      >
        Filters{activeCount > 0 ? ` (${activeCount})` : ''}
      </Button>
      <FilterSelects
        value={value}
        onChange={onChange}
        className="hidden items-center gap-3 sm:order-1 sm:flex"
      />
      <Modal open={sheetOpen} onClose={() => setSheetOpen(false)} title="Filters">
        <FilterSelects value={value} onChange={onChange} className="flex flex-col gap-3" />
        <Button type="button" fullWidth className="mt-4" onClick={() => setSheetOpen(false)}>
          Done
        </Button>
      </Modal>
    </div>
  );
};

export default CategoryFilterBar;
