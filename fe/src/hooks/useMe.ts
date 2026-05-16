import { useQuery } from '@tanstack/react-query';

import { getMe } from '@/api/auth';
import { queryKeys } from '@/api/queryKeys';
import { useAuth } from './useAuth';

export function useMe() {
  const { isAuthed } = useAuth();
  return useQuery({
    queryKey: queryKeys.me(),
    queryFn: getMe,
    enabled: isAuthed,
  });
}
