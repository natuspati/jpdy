import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface DecodedToken {
  sub: number;
  exp: number;
}

interface AuthState {
  token: string | null;
  userId: number | null;
  expiresAt: number | null;
  setToken: (token: string) => void;
  signOut: () => void;
}

function decode(token: string): DecodedToken | null {
  try {
    const [, payload] = token.split('.');
    if (!payload) return null;
    // JWT base64url → base64
    let padded = payload.replace(/-/g, '+').replace(/_/g, '/');
    while (padded.length % 4 !== 0) padded += '=';
    const json = atob(padded);
    const parsed = JSON.parse(json) as { sub?: unknown; exp?: unknown };
    // BE encodes `sub` as a string per JWT spec; coerce to number for our use.
    const sub = typeof parsed.sub === 'string' ? Number(parsed.sub) : parsed.sub;
    if (typeof sub !== 'number' || !Number.isFinite(sub) || typeof parsed.exp !== 'number') {
      return null;
    }
    return { sub, exp: parsed.exp };
  } catch {
    return null;
  }
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      userId: null,
      expiresAt: null,
      setToken: (token) => {
        const decoded = decode(token);
        if (!decoded) {
          set({ token: null, userId: null, expiresAt: null });
          return;
        }
        set({ token, userId: decoded.sub, expiresAt: decoded.exp * 1000 });
      },
      signOut: () => set({ token: null, userId: null, expiresAt: null }),
    }),
    {
      name: 'jpdy-auth',
      partialize: (s) => ({ token: s.token, userId: s.userId, expiresAt: s.expiresAt }),
    },
  ),
);

export function isAuthenticated(state: AuthState): boolean {
  if (!state.token || !state.expiresAt) return false;
  return state.expiresAt > Date.now();
}
