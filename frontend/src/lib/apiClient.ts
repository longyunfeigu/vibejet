import axios, { type AxiosError, type InternalAxiosRequestConfig } from 'axios';

import { clearSession, getSession, setSession } from '@/lib/authStore';
import { toSession, type TokenPairResponse } from '@/lib/tokenPair';

// VITE_API_URL 留空时 baseURL 为相对路径 `/api/v1`，由 Vite dev 代理转发到后端，避免 CORS。
// 设置为绝对地址(如 http://localhost:8010)时则直连后端。
const baseURL = `${import.meta.env.VITE_API_URL ?? ''}/api/v1`;

export const apiClient = axios.create({
  baseURL,
  withCredentials: true,
});

// 后端 /api/v1 为 Bearer 鉴权：每次请求从会话存储读取 access token 注入 Authorization 头。
// 登录态由 authStore 单一持有，这里只读；无会话时不加头(如登录、Google 换 token 等公开端点)。
apiClient.interceptors.request.use((config) => {
  const token = getSession()?.accessToken;
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// 发放 token 的公开端点：其自身 401 不应触发刷新(否则递归)；受保护端点(如 /auth/me)才触发。
const TOKEN_ENDPOINTS = [
  '/auth/login',
  '/auth/register',
  '/auth/refresh',
  '/auth/google',
  '/auth/oauth',
];

function isTokenEndpoint(url: string | undefined): boolean {
  return url !== undefined && TOKEN_ENDPOINTS.some((path) => url.includes(path));
}

interface RetriableConfig extends InternalAxiosRequestConfig {
  _retried?: boolean;
}

// 刷新失败的原因：status 为后端响应码；网络错误等拿不到响应时为 null。
class RefreshError extends Error {
  readonly status: number | null;

  constructor(message: string, status: number | null) {
    super(message);
    this.status = status;
  }
}

// 只有后端明确拒绝 refresh token(401/403)才说明会话真的失效；网络抖动、5xx、429 限流
// 都只是暂时刷新不了，不能因此把用户踢下线。
function refreshTokenRejected(err: unknown): boolean {
  return err instanceof RefreshError && (err.status === 401 || err.status === 403);
}

// 刷新走裸 fetch(不经 apiClient 拦截器)：既避免 access token 被注入，也保证刷新请求自身 401 时
// 不会再次进入下面的响应拦截器造成递归。信封解包用 lib/tokenPair 的唯一映射。
async function requestNewAccessToken(refreshToken: string): Promise<string> {
  const res = await fetch(`${baseURL}/auth/refresh`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify({ refresh_token: refreshToken }),
  });
  if (!res.ok) {
    throw new RefreshError(`refresh failed: ${res.status}`, res.status);
  }
  const body = (await res.json()) as { data: TokenPairResponse };
  // 刷新期间用户登出或换了账号：不能把旧会话写回存储，按刷新失败处理。
  if (getSession()?.refreshToken !== refreshToken) {
    throw new RefreshError('session changed during refresh', null);
  }
  const session = toSession(body.data);
  setSession(session);
  return session.accessToken;
}

// 单飞：同一个 refresh token 的并发 401 共享同一次刷新，避免打出 N 次刷新请求。
// 按 refresh token 区分：换了会话后不能加入旧会话那次（注定失败的）刷新。
let refreshInFlight: { refreshToken: string; promise: Promise<string> } | null = null;

function refreshAccessToken(refreshToken: string): Promise<string> {
  if (refreshInFlight?.refreshToken !== refreshToken) {
    const promise = requestNewAccessToken(refreshToken).finally(() => {
      if (refreshInFlight?.promise === promise) refreshInFlight = null;
    });
    refreshInFlight = { refreshToken, promise };
  }
  return refreshInFlight.promise;
}

// access token 过期 → 后端返回 401。首次命中时静默刷新一次并重放原请求；刷新失败则清会话。
apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const config = error.config as RetriableConfig | undefined;

    // 只处理受保护端点的首次 401；无响应错误、非 401、已重试、发 token 端点一律原样抛出。
    if (
      !config ||
      error.response?.status !== 401 ||
      config._retried ||
      isTokenEndpoint(config.url)
    ) {
      return Promise.reject(error);
    }

    const session = getSession();
    if (!session) {
      // 无会话可用：不尝试刷新，直接抛出原错误。
      return Promise.reject(error);
    }

    // 请求发出后会话已经变了(别的请求已刷新完，或换了账号)：401 属于旧 token，
    // 直接用当前 token 重放一次，不再刷新、也不能因此清掉新会话。
    if (config.headers.Authorization !== `Bearer ${session.accessToken}`) {
      config._retried = true;
      config.headers.Authorization = `Bearer ${session.accessToken}`;
      return apiClient(config);
    }

    const { refreshToken } = session;

    let accessToken: string;
    try {
      accessToken = await refreshAccessToken(refreshToken);
    } catch (refreshError) {
      // refresh token 被拒：清会话(经 authStore 连带清空 query 缓存)。其余失败保留会话，
      // 由页面的错误态提供重试。两种情况都抛出原始错误，不再重试。
      // 只清本次刷新所属的会话；刷新期间已换成的新会话不受影响。
      if (refreshTokenRejected(refreshError) && getSession()?.refreshToken === refreshToken) {
        clearSession();
      }
      return Promise.reject(error);
    }

    // 刷新成功：用新 token 重放原请求一次(config._retried 已置位，重放再 401 不会二次刷新)。
    config._retried = true;
    config.headers.Authorization = `Bearer ${accessToken}`;
    return apiClient(config);
  },
);
