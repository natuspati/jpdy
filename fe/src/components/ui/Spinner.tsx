const Spinner = ({ className = '' }: { className?: string }) => (
  <span
    className={`inline-block h-5 w-5 animate-spin rounded-full border-2 border-slate-500 border-t-amber-400 ${className}`}
    role="status"
    aria-label="Loading"
  />
);

export default Spinner;
