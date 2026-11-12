import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import {
  createMemoryHistory,
  createRootRoute,
  createRouter,
  RouterProvider,
} from '@tanstack/react-router';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { clearSession, setSession } from '@/lib/authStore';

import { HomeError } from './HomeError';

function renderHomeError() {
  const router = createRouter({
    routeTree: createRootRoute({ component: HomeError }),
    history: createMemoryHistory({ initialEntries: ['/'] }),
  });
  render(
    <QueryClientProvider client={new QueryClient()}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  );
  return router;
}

afterEach(() => {
  clearSession();
  vi.restoreAllMocks();
});

describe('HomeError', () => {
  it('会话已被清掉：提示会话失效，只给重新登录', async () => {
    renderHomeError();

    expect(await screen.findByRole('heading', { name: '会话已失效' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '重新登录' })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: '重试' })).not.toBeInTheDocument();
  });

  it('会话还在（服务暂时不可用）：给重试，点击重新加载路由', async () => {
    setSession({ accessToken: 'a', refreshToken: 'r' });
    const router = renderHomeError();
    const invalidate = vi.spyOn(router, 'invalidate');

    expect(await screen.findByRole('heading', { name: '暂时无法加载' })).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: '重试' }));

    expect(invalidate).toHaveBeenCalledTimes(1);
  });
});
