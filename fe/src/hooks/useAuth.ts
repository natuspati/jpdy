import { useAuthStore, isAuthenticated } from '@/store/authStore';

export function useAuth() {
  const token = useAuthStore((s) => s.token);
  const userId = useAuthStore((s) => s.userId);
  const expiresAt = useAuthStore((s) => s.expiresAt);
  const signOut = useAuthStore((s) => s.signOut);
  const setToken = useAuthStore((s) => s.setToken);
  return {
    token,
    userId,
    isAuthed: isAuthenticated({ token, userId, expiresAt, setToken, signOut }),
    signOut,
    setToken,
  };
}
