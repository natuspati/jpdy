import { type FC, useState } from 'react';

import Button from '@/components/ui/Button';
import FilterSelect from '@/components/ui/FilterSelect';
import Input from '@/components/ui/Input';
import Modal from '@/components/ui/Modal';
import { type AdminUserFilters, activeAdminFilterCount } from './adminUserFilters';

interface Props {
  value: AdminUserFilters;
  onChange: (value: AdminUserFilters) => void;
}

const ROLE_OPTIONS = [
  { value: 'all', label: 'All' },
  { value: 'generic', label: 'Generic' },
  { value: 'admin', label: 'Admin' },
] as const satisfies ReadonlyArray<{ value: AdminUserFilters['role']; label: string }>;

const DateField: FC<{ label: string; value: string; onChange: (value: string) => void }> = ({
  label,
  value,
  onChange,
}) => (
  <label className="flex items-center justify-between gap-2 text-xs text-slate-400">
    {label}
    <Input
      type="date"
      className="h-9 w-auto py-1 text-sm"
      value={value}
      onChange={(event) => onChange(event.target.value)}
    />
  </label>
);

const FilterFields: FC<Props & { className: string }> = ({ value, onChange, className }) => (
  <div className={className}>
    <FilterSelect
      label="Role"
      value={value.role}
      options={ROLE_OPTIONS}
      onChange={(role) => onChange({ ...value, role })}
    />
    <DateField
      label="From"
      value={value.createdFrom}
      onChange={(createdFrom) => onChange({ ...value, createdFrom })}
    />
    <DateField
      label="To"
      value={value.createdTo}
      onChange={(createdTo) => onChange({ ...value, createdTo })}
    />
  </div>
);

/** Username search plus role, and registration dates. On mobile the rest opens in a bottom sheet. */
const UserFilterBar: FC<Props> = ({ value, onChange }) => {
  const [sheetOpen, setSheetOpen] = useState(false);
  const activeCount = activeAdminFilterCount(value);

  return (
    <div className="flex w-full flex-wrap items-center gap-2">
      <Input
        type="search"
        aria-label="Search users"
        placeholder="Search users"
        className="h-9 w-full py-1 sm:w-48"
        value={value.username}
        onChange={(event) => onChange({ ...value, username: event.target.value })}
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
      <FilterFields
        value={value}
        onChange={onChange}
        className="hidden flex-wrap items-center gap-3 sm:flex"
      />
      <Modal open={sheetOpen} onClose={() => setSheetOpen(false)} title="Filters">
        <FilterFields value={value} onChange={onChange} className="flex flex-col gap-3" />
        <Button type="button" fullWidth className="mt-4" onClick={() => setSheetOpen(false)}>
          Done
        </Button>
      </Modal>
    </div>
  );
};

export default UserFilterBar;
