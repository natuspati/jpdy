import { useEffect, useState } from 'react';

/**
 * Returns the remaining whole seconds (`>= 0`) until `deadlineIso`. Re-renders
 * every 200ms while active. Returns `null` if `deadlineIso` is null.
 */
export function useCountdown(deadlineIso: string | null): number | null {
  const [remaining, setRemaining] = useState<number | null>(() =>
    deadlineIso ? Math.max(0, Math.ceil((Date.parse(deadlineIso) - Date.now()) / 1000)) : null,
  );

  useEffect(() => {
    if (!deadlineIso) {
      setRemaining(null);
      return;
    }
    const deadline = Date.parse(deadlineIso);
    const tick = () => {
      const left = Math.max(0, Math.ceil((deadline - Date.now()) / 1000));
      setRemaining(left);
      if (left === 0) window.clearInterval(handle);
    };
    tick();
    const handle = window.setInterval(tick, 200);
    return () => window.clearInterval(handle);
  }, [deadlineIso]);

  return remaining;
}
