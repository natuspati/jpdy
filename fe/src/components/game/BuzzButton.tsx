interface Props {
  enabled: boolean;
  onBuzz: () => void;
  disabledReason?: string;
}

const BuzzerIcon = () => (
  <svg aria-hidden="true" viewBox="0 0 64 64" className="h-9 w-9 fill-current">
    <path d="M20 29h24l5 11H15l5-11Zm3-14h18v11H23V15Zm-3 28h24v6H20v-6Zm7 9h10v5H27v-5Z" />
  </svg>
);

const BuzzButton = ({ enabled, onBuzz, disabledReason }: Props) => (
  <div className="mx-auto flex flex-col items-center gap-1">
    <button
      type="button"
      disabled={!enabled}
      onClick={onBuzz}
      className={`flex size-36 flex-col items-center justify-center rounded-full border-b-8 text-xl font-black uppercase tracking-wider transition-all focus:outline-none focus:ring-2 focus:ring-amber-400 focus:ring-offset-2 focus:ring-offset-slate-950 sm:size-40 sm:text-2xl ${
        enabled
          ? 'border-rose-800 bg-rose-500 text-white shadow-lg shadow-rose-950/30 hover:bg-rose-400 active:translate-y-2 active:border-b-0 active:shadow-none'
          : 'translate-y-2 border-slate-950 bg-slate-800 text-slate-500 shadow-inner shadow-slate-950/70'
      }`}
    >
      <BuzzerIcon />
      Buzz
    </button>
    {!enabled && disabledReason ? (
      <p className="text-center text-sm text-slate-400">{disabledReason}</p>
    ) : null}
  </div>
);

export default BuzzButton;
