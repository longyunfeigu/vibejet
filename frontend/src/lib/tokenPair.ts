import type { Session } from '@/lib/authStore';

// 后端 /auth/login、/auth/refresh 等发 token 端点的 data 载荷形状。
// 字段改名/增删只改这里，编译期同时暴露 apiClient 与 authApi 的所有用点。
export interface TokenPairResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export function toSession(d: Pick<TokenPairResponse, 'access_token' | 'refresh_token'>): Session {
  return { accessToken: d.access_token, refreshToken: d.refresh_token };
}
