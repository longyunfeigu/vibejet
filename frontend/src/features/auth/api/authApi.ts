// input: apiClient (POST /auth/login, /auth/google, GET /auth/me), 后端响应信封 { code, message, data }
// output: login(input) -> TokenPair, loginWithGoogle(code) -> TokenPair, fetchMe() -> CurrentUser
// owner: wanhua.gu
// pos: auth feature - 后端接口封装(解包信封 + snake_case→camelCase)；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
import { apiClient } from '@/lib/apiClient'

import type { CurrentUser, LoginInput, TokenPair } from '../types'

interface ApiEnvelope<T> {
  code: number
  message: string
  data: T
}

interface TokenPairResponse {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
}

interface UserResponse {
  id: number
  username: string
  email: string
  full_name: string | null
  is_active: boolean
  is_superuser: boolean
}

function mapTokenPair(d: TokenPairResponse): TokenPair {
  return {
    accessToken: d.access_token,
    refreshToken: d.refresh_token,
    tokenType: d.token_type,
    expiresIn: d.expires_in,
  }
}

export async function login(input: LoginInput): Promise<TokenPair> {
  const res = await apiClient.post<ApiEnvelope<TokenPairResponse>>('/auth/login', input)
  return mapTokenPair(res.data.data)
}

export async function loginWithGoogle(code: string): Promise<TokenPair> {
  const res = await apiClient.post<ApiEnvelope<TokenPairResponse>>('/auth/google', { code })
  return mapTokenPair(res.data.data)
}

export async function fetchMe(): Promise<CurrentUser> {
  const res = await apiClient.get<ApiEnvelope<UserResponse>>('/auth/me')
  const u = res.data.data
  return {
    id: u.id,
    username: u.username,
    email: u.email,
    fullName: u.full_name,
    isActive: u.is_active,
    isSuperuser: u.is_superuser,
  }
}
