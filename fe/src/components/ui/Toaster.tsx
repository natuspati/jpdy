import { useToastStore, type Toast } from '@/store/toastStore';

const toneClasses: Record<Toast['kind'], string> = {
  info: 'bg-sky-700 text-sky-50',
  success: 'bg-emerald-700 text-emerald-50',
  error: 'bg-rose-700 text-rose-50',
};

const Toaster = () => {
  const toasts = useToastStore((s) => s.toasts);
  const dismiss = useToastStore((s) => s.dismiss);
  return (
    <div className="pointer-events-none fixed inset-x-0 top-2 z-[60] flex flex-col items-center gap-2 px-2">
      {toasts.map((t) => (
        <button
          key={t.id}
          className={`pointer-events-auto w-full max-w-sm rounded-md px-4 py-2 text-left text-sm shadow-lg ${toneClasses[t.kind]}`}
          onClick={() => dismiss(t.id)}
        >
          {t.text}
        </button>
      ))}
    </div>
  );
};

export default Toaster;
