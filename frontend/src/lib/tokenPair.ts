// input: 后端 token 对信封字段(snake_case: access_token/refresh_token/token_type/expires_in)
// output: TokenPairResponse 类型 + toSession(d) —— token 信封形状的唯一权威声明
// owner: wanhua.gu
// pos: 跨域基础设施 - token 信封映射(apiClient 静默刷新与 auth feature 共用，杜绝双份解包漂移)；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
import type { Session } from '@/lib/authStore'

// 后端 /auth/login、/auth/refresh 等发 token 端点的 data 载荷形状。
// 字段改名/增删只改这里，编译期同时暴露 apiClient 与 authApi 的所有用点。
export interface TokenPairResponse {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
}

export function toSession(d: Pick<TokenPairResponse, 'access_token' | 'refresh_token'>): Session {
  return { accessToken: d.access_token, refreshToken: d.refresh_token }
}
