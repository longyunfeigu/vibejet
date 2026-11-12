import type { AxiosResponse } from 'axios';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { apiClient } from '@/lib/apiClient';

import { fetchMe } from './authApi';

afterEach(() => {
  vi.restoreAllMocks();
});

describe('fetchMe', () => {
  it('把 AbortSignal 透传给 apiClient.get', async () => {
    const getSpy = vi.spyOn(apiClient, 'get').mockResolvedValue({
      data: {
        code: 0,
        message: 'ok',
        data: {
          id: 1,
          username: 'alice',
          email: 'alice@example.com',
          full_name: null,
          is_active: true,
          is_superuser: false,
        },
      },
    } as unknown as AxiosResponse);
    const controller = new AbortController();

    await fetchMe(controller.signal);

    expect(getSpy).toHaveBeenCalledWith('/auth/me', { signal: controller.signal });
  });
});
