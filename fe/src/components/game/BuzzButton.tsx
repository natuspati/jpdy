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
  <div className="space-y-2">
    <button
      type="button"
      disabled={!enabled}
      onClick={onBuzz}
      className={`flex w-full items-center justify-center gap-3 rounded-xl py-8 text-3xl font-black uppercase tracking-wider transition-colors focus:outline-none focus:ring-2 focus:ring-amber-400 focus:ring-offset-2 focus:ring-offset-slate-950 ${
        enabled
          ? 'bg-rose-500 text-white hover:bg-rose-400 active:bg-rose-600'
          : 'bg-slate-800 text-slate-500'
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
