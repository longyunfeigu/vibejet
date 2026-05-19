// input: (TODO) backend auth endpoints / JWT storage
// output: useAuth hook - 占位实现，永远返回未登录状态
// owner: unknown
// pos: 通用 hook - useAuth（占位）；一旦我被更新，务必更新我的开头注释以及所属文件夹的md

export interface AuthUser {
  id: string;
  username: string;
}

export interface AuthState {
  user: AuthUser | null;
  isAuthenticated: boolean;
}

/**
 * Placeholder useAuth - returns "unauthenticated" until auth is wired up.
 *
 * TODO: integrate with backend auth flow (JWT / session cookie).
 *   - login(credentials) -> POST /api/v1/auth/login -> store token
 *   - logout() -> POST /api/v1/auth/logout -> clear token
 *   - whoami() -> GET /api/v1/auth/me -> populate user
 *   - hook apiClient interceptor for Bearer header
 */
export const useAuth = (): AuthState => ({
  user: null,
  isAuthenticated: false,
});
