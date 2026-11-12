import { useSuspenseQuery } from '@tanstack/react-query';

import { fetchMe } from '@/features/auth';

export function useCurrentUser() {
  return useSuspenseQuery({ queryKey: ['auth', 'me'], queryFn: ({ signal }) => fetchMe(signal) });
}
