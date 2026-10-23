interface Props<T extends string> {
  label: string;
  value: T;
  options: ReadonlyArray<{ value: T; label: string }>;
  onChange: (value: T) => void;
}

const selectClass =
  'h-9 rounded-md border border-slate-700 bg-slate-950 px-2 text-sm text-slate-100';

// Narrows the raw <select> string back to one of the option values.
const parseOption = <T extends string>(options: ReadonlyArray<{ value: T }>, raw: string): T =>
  options.find((option) => option.value === raw)?.value ?? options[0].value;

const FilterSelect = <T extends string>({ label, value, options, onChange }: Props<T>) => (
  <label className="flex items-center justify-between gap-2 text-xs text-slate-400">
    {label}
    <select
      className={selectClass}
      value={value}
      onChange={(event) => onChange(parseOption(options, event.target.value))}
    >
      {options.map((option) => (
        <option key={option.value} value={option.value}>
          {option.label}
        </option>
      ))}
    </select>
  </label>
);

export default FilterSelect;
