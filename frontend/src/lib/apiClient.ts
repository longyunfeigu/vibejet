// input: axios, VITE_API_URL 环境变量(留空 → 相对路径走 Vite /api 代理), authStore(getSession/setSession/clearSession)
// output: apiClient —— axios 实例(baseURL=${VITE_API_URL}/api/v1, withCredentials, 注入 Bearer + 401 单飞刷新)
// owner: wanhua.gu
// pos: 跨域基础设施 - HTTP 客户端(后端 /api/v1 接口的统一入口 + 鉴权头注入 + token 刷新)；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
import axios, { type AxiosError, type InternalAxiosRequestConfig } from 'axios'

import { clearSession, getSession, setSession } from '@/lib/authStore'
import { toSession, type TokenPairResponse } from '@/lib/tokenPair'

// VITE_API_URL 留空时 baseURL 为相对路径 `/api/v1`，由 Vite dev 代理转发到后端，避免 CORS。
// 设置为绝对地址(如 http://localhost:8000)时则直连后端。
const baseURL = `${import.meta.env.VITE_API_URL ?? ''}/api/v1`

export const apiClient = axios.create({
  baseURL,
  withCredentials: true,
})

// 后端 /api/v1 为 Bearer 鉴权：每次请求从会话存储读取 access token 注入 Authorization 头。
// 登录态由 authStore 单一持有，这里只读；无会话时不加头(如登录、Google 换 token 等公开端点)。
apiClient.interceptors.request.use((config) => {
  const token = getSession()?.accessToken
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// 发放 token 的公开端点：其自身 401 不应触发刷新(否则递归)；受保护端点(如 /auth/me)才触发。
const TOKEN_ENDPOINTS = ['/auth/login', '/auth/register', '/auth/refresh', '/auth/google', '/auth/oauth']

function isTokenEndpoint(url: string | undefined): boolean {
  return url !== undefined && TOKEN_ENDPOINTS.some((path) => url.includes(path))
}

interface RetriableConfig extends InternalAxiosRequestConfig {
  _retried?: boolean
}

// 刷新走裸 fetch(不经 apiClient 拦截器)：既避免 access token 被注入，也保证刷新请求自身 401 时
// 不会再次进入下面的响应拦截器造成递归。信封解包用 lib/tokenPair 的唯一映射。
async function requestNewAccessToken(refreshToken: string): Promise<string> {
  const res = await fetch(`${baseURL}/auth/refresh`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify({ refresh_token: refreshToken }),
  })
  if (!res.ok) {
    throw new Error(`refresh failed: ${res.status}`)
  }
  const body = (await res.json()) as { data: TokenPairResponse }
  const session = toSession(body.data)
  setSession(session)
  return session.accessToken
}

// 单飞：并发的多个 401 共享同一次刷新，避免打出 N 次刷新请求。
let refreshInFlight: Promise<string> | null = null

function refreshAccessToken(refreshToken: string): Promise<string> {
  if (!refreshInFlight) {
    refreshInFlight = requestNewAccessToken(refreshToken).finally(() => {
      refreshInFlight = null
    })
  }
  return refreshInFlight
}

// access token 过期 → 后端返回 401。首次命中时静默刷新一次并重放原请求；刷新失败则清会话。
apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const config = error.config as RetriableConfig | undefined

    // 只处理受保护端点的首次 401；无响应错误、非 401、已重试、发 token 端点一律原样抛出。
    if (!config || error.response?.status !== 401 || config._retried || isTokenEndpoint(config.url)) {
      return Promise.reject(error)
    }

    const refreshToken = getSession()?.refreshToken
    if (!refreshToken) {
      // 无 refresh token 可用：不尝试刷新，直接抛出原错误。
      return Promise.reject(error)
    }

    let accessToken: string
    try {
      accessToken = await refreshAccessToken(refreshToken)
    } catch {
      // 刷新失败：清会话(经 authStore 连带清空 query 缓存)，抛出原始错误，不再重试。
      clearSession()
      return Promise.reject(error)
    }

    // 刷新成功：用新 token 重放原请求一次(config._retried 已置位，重放再 401 不会二次刷新)。
    config._retried = true
    config.headers.Authorization = `Bearer ${accessToken}`
    return apiClient(config)
  },
)
