import { useSyncExternalStore } from 'react';

import { clearSession, getSession, subscribe, type Session } from '@/lib/authStore';

export interface UseAuthResult {
  session: Session | null;
  isAuthenticated: boolean;
  logout: () => void;
}

export function useAuth(): UseAuthResult {
  const session = useSyncExternalStore(subscribe, getSession, getSession);
  return {
    session,
    isAuthenticated: session !== null,
    logout: clearSession,
  };
}
