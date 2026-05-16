interface Props {
  enabled: boolean;
  onBuzz: () => void;
}

const BuzzButton = ({ enabled, onBuzz }: Props) => (
  <button
    type="button"
    disabled={!enabled}
    onClick={onBuzz}
    className={`sticky bottom-0 left-0 right-0 z-10 -mx-4 block w-[calc(100%+2rem)] py-6 text-3xl font-black uppercase tracking-wider transition-colors sm:static sm:m-0 sm:w-full sm:rounded-lg sm:py-10 ${
      enabled
        ? 'bg-rose-500 text-white hover:bg-rose-400 active:bg-rose-600'
        : 'bg-slate-800 text-slate-500'
    }`}
  >
    Buzz!
  </button>
);

export default BuzzButton;
