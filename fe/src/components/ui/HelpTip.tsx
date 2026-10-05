import { useEffect, useId, useRef, useState } from 'react';

interface Props {
  text: string;
}

// Shows on hover, keyboard focus, or tap; a tap outside closes it, so it also works on touch screens.
const HelpTip = ({ text }: Props) => {
  const id = useId();
  const rootRef = useRef<HTMLSpanElement>(null);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    if (!open) return;
    const closeOnOutsidePress = (event: PointerEvent) => {
      if (!rootRef.current?.contains(event.target as Node)) setOpen(false);
    };
    document.addEventListener('pointerdown', closeOnOutsidePress);
    return () => document.removeEventListener('pointerdown', closeOnOutsidePress);
  }, [open]);

  return (
    <span ref={rootRef} className="group relative inline-flex">
      <button
        type="button"
        aria-label="More info"
        aria-describedby={id}
        aria-expanded={open}
        onClick={() => setOpen((value) => !value)}
        onKeyDown={(event) => {
          if (event.key === 'Escape') setOpen(false);
        }}
        className="inline-flex h-4 w-4 items-center justify-center rounded-full border border-slate-600 text-[10px] font-bold leading-none text-slate-400 hover:text-amber-300 focus:outline-none focus:ring-2 focus:ring-amber-400"
      >
        ?
      </button>
      <span
        id={id}
        role="tooltip"
        className={`pointer-events-none absolute left-0 top-full z-20 mt-1 w-56 rounded-md border border-slate-700 bg-slate-900 px-2 py-1.5 text-xs font-normal text-slate-200 shadow-xl group-focus-within:visible group-hover:visible ${
          open ? 'visible' : 'invisible'
        }`}
      >
        {text}
      </span>
    </span>
  );
};

export default HelpTip;
