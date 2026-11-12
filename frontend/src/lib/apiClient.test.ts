import {
  AxiosError,
  AxiosHeaders,
  type AxiosResponse,
  type InternalAxiosRequestConfig,
} from 'axios';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { apiClient } from '@/lib/apiClient';
import { clearSession, getSession, setSession } from '@/lib/authStore';

function okResponse(config: InternalAxiosRequestConfig): AxiosResponse {
  return { data: { ok: true }, status: 200, statusText: 'OK', headers: new AxiosHeaders(), config };
}

function unauthorized(config: InternalAxiosRequestConfig): AxiosError {
  return new AxiosError('Unauthorized', 'ERR_BAD_REQUEST', config, null, {
    data: { code: 401, message: 'unauthorized', data: null },
    status: 401,
    statusText: 'Unauthorized',
    headers: new AxiosHeaders(),
    config,
  });
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
    );
  });
}

afterEach(() => {
  clearSession();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
  apiClient.defaults.adapter = undefined;
});

describe('apiClient 401 单飞刷新拦截器', () => {
  beforeEach(() => {
    setSession({ accessToken: 'old-access', refreshToken: 'old-refresh' });
  });

  it('并发 401 只触发一次刷新，两个原请求都用新 token 重放并成功', async () => {
    const fetchMock = vi.fn(refreshOk);
    vi.stubGlobal('fetch', fetchMock);
    apiClient.defaults.adapter = async (config) => {
      if (config.headers.Authorization === 'Bearer new-access') return okResponse(config);
      throw unauthorized(config);
    };

    const [r1, r2] = await Promise.all([
      apiClient.get('/protected-a'),
      apiClient.get('/protected-b'),
    ]);

    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(r1.status).toBe(200);
    expect(r2.status).toBe(200);
    expect(getSession()).toEqual({ accessToken: 'new-access', refreshToken: 'new-refresh' });
  });

  it('刷新失败时清会话并抛出原始错误，刷新端点自身 401 不再触发刷新', async () => {
    const fetchMock = vi.fn(async () => ({ ok: false, status: 401, json: async () => ({}) }));
    vi.stubGlobal('fetch', fetchMock);
    apiClient.defaults.adapter = async (config) => {
      throw unauthorized(config);
    };

    await expect(apiClient.get('/protected')).rejects.toBeInstanceOf(AxiosError);
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(getSession()).toBeNull();
  });

  it('refresh token 被拒(403)同样清会话', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => ({ ok: false, status: 403, json: async () => ({}) })),
    );
    apiClient.defaults.adapter = async (config) => {
      throw unauthorized(config);
    };

    await expect(apiClient.get('/protected')).rejects.toBeInstanceOf(AxiosError);
    expect(getSession()).toBeNull();
  });

  it.each([
    ['5xx', async () => ({ ok: false, status: 503, json: async () => ({}) })],
    ['429 限流', async () => ({ ok: false, status: 429, json: async () => ({}) })],
    [
      '网络错误',
      async () => {
        throw new TypeError('Failed to fetch');
      },
    ],
  ])('刷新暂时失败(%s)：抛出原始错误，但不清会话', async (_label, refresh) => {
    vi.stubGlobal('fetch', vi.fn(refresh));
    apiClient.defaults.adapter = async (config) => {
      throw unauthorized(config);
    };

    await expect(apiClient.get('/protected')).rejects.toBeInstanceOf(AxiosError);
    expect(getSession()).toEqual({ accessToken: 'old-access', refreshToken: 'old-refresh' });
  });

  it('刷新期间登出：刷新结果不写回会话', async () => {
    vi.stubGlobal('fetch', vi.fn(refreshOk));
    apiClient.defaults.adapter = async (config) => {
      if (config.headers.Authorization === 'Bearer new-access') return okResponse(config);
      throw unauthorized(config);
    };

    const pending = apiClient.get('/protected');
    await new Promise((resolve) => setTimeout(resolve, 0));
    clearSession();

    await expect(pending).rejects.toBeInstanceOf(AxiosError);
    expect(getSession()).toBeNull();
  });

  it('刷新期间换了账号：新会话不被覆盖也不被清掉', async () => {
    vi.stubGlobal('fetch', vi.fn(refreshOk));
    apiClient.defaults.adapter = async (config) => {
      throw unauthorized(config);
    };

    const pending = apiClient.get('/protected');
    await new Promise((resolve) => setTimeout(resolve, 0));
    setSession({ accessToken: 'other-access', refreshToken: 'other-refresh' });

    await expect(pending).rejects.toBeInstanceOf(AxiosError);
    expect(getSession()).toEqual({ accessToken: 'other-access', refreshToken: 'other-refresh' });
  });

  it('换账号后才到的旧会话 401：不加入旧刷新、不清新会话，用新 token 重放', async () => {
    const fetchMock = vi.fn(refreshOk);
    vi.stubGlobal('fetch', fetchMock);
    // 旧 token 的请求：第一个立即 401，第二个等到换账号之后才回 401
    let releaseLate: () => void = () => {};
    const lateGate = new Promise<void>((resolve) => {
      releaseLate = resolve;
    });
    apiClient.defaults.adapter = async (config) => {
      if (config.headers.Authorization === 'Bearer other-access') return okResponse(config);
      if (config.url === '/late') await lateGate;
      throw unauthorized(config);
    };

    const early = apiClient.get('/early');
    const late = apiClient.get('/late');
    await new Promise((resolve) => setTimeout(resolve, 0));
    setSession({ accessToken: 'other-access', refreshToken: 'other-refresh' });
    releaseLate();

    const lateResponse = await late;
    await expect(early).rejects.toBeInstanceOf(AxiosError);
    expect(lateResponse.status).toBe(200);
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(getSession()).toEqual({ accessToken: 'other-access', refreshToken: 'other-refresh' });
  });
});
