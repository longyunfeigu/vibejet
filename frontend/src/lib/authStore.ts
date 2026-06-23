// input: localStorage('vibejet.session'), Session{accessToken, refreshToken}
// output: type Session + getSession/setSession/clearSession/subscribe(useSyncExternalStore 兼容的会话外部存储)
// owner: wanhua.gu
// pos: 跨域基础设施 - 客户端会话存储(token 持久化 + 变更订阅)；一旦我被更新，务必更新我的开头注释以及所属文件夹的md

const STORAGE_KEY = 'vibejet.session'

export interface Session {
  accessToken: string
  refreshToken: string
}

const listeners = new Set<() => void>()

function readFromStorage(): Session | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return null
    const parsed = JSON.parse(raw) as Partial<Session>
    if (typeof parsed.accessToken === 'string' && typeof parsed.refreshToken === 'string') {
      return { accessToken: parsed.accessToken, refreshToken: parsed.refreshToken }
    }
    return null
  } catch {
    return null
  }
}

// 模块级单一引用：仅在 set/clear 时变更，保证 useSyncExternalStore 的快照引用稳定。
let currentSession: Session | null = readFromStorage()

function emit() {
  for (const listener of listeners) listener()
}

export function getSession(): Session | null {
  return currentSession
}

export function setSession(session: Session): void {
  currentSession = session
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(session))
  } catch {
    // 持久化失败(如隐私模式禁用 storage)不应阻断登录，内存态已更新。
  }
  emit()
}

export function clearSession(): void {
  currentSession = null
  try {
    localStorage.removeItem(STORAGE_KEY)
  } catch {
    // ignore
  }
  emit()
}

export function subscribe(listener: () => void): () => void {
  listeners.add(listener)
  return () => {
    listeners.delete(listener)
  }
}
