// input: apiClient(401 单飞刷新), authStore, 全局 fetch(mock) + axios adapter(mock)
// output: apiClient 拦截器测试(401 并发单飞刷新 + 刷新失败清会话)
// owner: wanhua.gu
// pos: 跨域基础设施 - apiClient 测试；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
import { AxiosError, AxiosHeaders, type AxiosResponse, type InternalAxiosRequestConfig } from 'axios'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { apiClient } from '@/lib/apiClient'
import { clearSession, getSession, setSession } from '@/lib/authStore'

function okResponse(config: InternalAxiosRequestConfig): AxiosResponse {
  return { data: { ok: true }, status: 200, statusText: 'OK', headers: new AxiosHeaders(), config }
}

function unauthorized(config: InternalAxiosRequestConfig): AxiosError {
  return new AxiosError('Unauthorized', 'ERR_BAD_REQUEST', config, null, {
    data: { code: 401, message: 'unauthorized', data: null },
    status: 401,
    statusText: 'Unauthorized',
    headers: new AxiosHeaders(),
    config,
  })
}

// 刷新成功信封：延迟一个 macrotask 返回，确保并发的两个 401 都在刷新未完成的窗口内合并到同一单飞。
function refreshOk() {
  return new Promise((resolve) => {
    setTimeout(
      () =>
        resolve({
          ok: true,
          json: async () => ({
            code: 0,
            message: 'ok',
            data: {
              access_token: 'new-access',
              refresh_token: 'new-refresh',
              token_type: 'bearer',
              expires_in: 3600,
            },
          }),
        }),
      10,
    )
  })
}

afterEach(() => {
  clearSession()
  vi.restoreAllMocks()
  vi.unstubAllGlobals()
  apiClient.defaults.adapter = undefined
})

describe('apiClient 401 单飞刷新拦截器', () => {
  beforeEach(() => {
    setSession({ accessToken: 'old-access', refreshToken: 'old-refresh' })
  })

  it('并发 401 只触发一次刷新，两个原请求都用新 token 重放并成功', async () => {
    const fetchMock = vi.fn(refreshOk)
    vi.stubGlobal('fetch', fetchMock)
    apiClient.defaults.adapter = async (config) => {
      if (config.headers.Authorization === 'Bearer new-access') return okResponse(config)
      throw unauthorized(config)
    }

    const [r1, r2] = await Promise.all([apiClient.get('/protected-a'), apiClient.get('/protected-b')])

    expect(fetchMock).toHaveBeenCalledTimes(1)
    expect(r1.status).toBe(200)
    expect(r2.status).toBe(200)
    expect(getSession()).toEqual({ accessToken: 'new-access', refreshToken: 'new-refresh' })
  })

  it('刷新失败时清会话并抛出原始错误，刷新端点自身 401 不再触发刷新', async () => {
    const fetchMock = vi.fn(async () => ({ ok: false, status: 401, json: async () => ({}) }))
    vi.stubGlobal('fetch', fetchMock)
    apiClient.defaults.adapter = async (config) => {
      throw unauthorized(config)
    }

    await expect(apiClient.get('/protected')).rejects.toBeInstanceOf(AxiosError)
    expect(fetchMock).toHaveBeenCalledTimes(1)
    expect(getSession()).toBeNull()
  })
})
