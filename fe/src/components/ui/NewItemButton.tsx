import { type FC } from 'react';

import Button from './Button';

interface NewItemButtonProps {
  label: string;
  onClick: () => void;
}

const PlusIcon: FC = () => (
  <svg
    aria-hidden="true"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeLinecap="round"
    strokeWidth="3"
    className="h-[1.375rem] w-[1.375rem]"
  >
    <path d="M12 5v14M5 12h14" />
  </svg>
);

const NewItemButton: FC<NewItemButtonProps> = ({ label, onClick }) => (
  <div className="group relative">
    <Button aria-label={label} size="icon" title={label} onClick={onClick} className="shrink-0">
      <PlusIcon />
    </Button>
    <span
      role="tooltip"
      className="pointer-events-none absolute left-1/2 top-full z-10 mt-2 -translate-x-1/2 whitespace-nowrap rounded bg-slate-700 px-2 py-1 text-xs font-medium text-slate-50 opacity-0 shadow transition-opacity group-hover:opacity-100 group-focus-within:opacity-100"
    >
      {label}
    </span>
  </div>
);

export default NewItemButton;
