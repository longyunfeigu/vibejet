// input: authStore (getSession/subscribe/clearSession)
// output: useAuth() React hook —— { session, isAuthenticated, logout }
// owner: wanhua.gu
// pos: 跨域 hook - 会话的 React 门面(useSyncExternalStore 订阅 authStore)；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
import { useSyncExternalStore } from 'react'

import { clearSession, getSession, subscribe, type Session } from '@/lib/authStore'

export interface UseAuthResult {
  session: Session | null
  isAuthenticated: boolean
  logout: () => void
}

export function useAuth(): UseAuthResult {
  const session = useSyncExternalStore(subscribe, getSession, getSession)
  return {
    session,
    isAuthenticated: session !== null,
    logout: clearSession,
  }
}
