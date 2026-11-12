import { useQueryErrorResetBoundary } from '@tanstack/react-query';
import { useNavigate, useRouter } from '@tanstack/react-router';
import { useEffect } from 'react';

import { Button } from '@/components/ui/button';
import { clearSession, getSession } from '@/lib/authStore';

// 首页路由的错误态。会话已被清掉（refresh token 被后端拒绝）→ 只能重新登录；
// 会话还在（网络抖动、服务 5xx、限流等）→ 给重试，不把用户踢下线。
export function HomeError() {
  const navigate = useNavigate();
  const router = useRouter();
  const queryErrorResetBoundary = useQueryErrorResetBoundary();

  // 让 Suspense 查询在重试时真正重新请求，而不是直接重放上次的错误
  useEffect(() => {
    queryErrorResetBoundary.reset();
  }, [queryErrorResetBoundary]);

  function backToLogin() {
    clearSession();
    void navigate({ to: '/login' });
  }

  if (!getSession()) {
    return (
      <div className="bg-background flex min-h-[100dvh] flex-col items-center justify-center gap-4 px-4 text-center">
        <div className="flex max-w-sm flex-col gap-2">
          <h1 className="text-xl font-semibold tracking-tight">会话已失效</h1>
          <p className="text-muted-foreground text-sm">请重新登录后继续使用 vibejet。</p>
        </div>
        <Button onClick={backToLogin} className="rounded-lg">
          重新登录
        </Button>
      </div>
    );
  }

  return (
    <div className="bg-background flex min-h-[100dvh] flex-col items-center justify-center gap-4 px-4 text-center">
      <div className="flex max-w-sm flex-col gap-2">
        <h1 className="text-xl font-semibold tracking-tight">暂时无法加载</h1>
        <p className="text-muted-foreground text-sm">网络或服务暂时不可用，请稍后重试。</p>
      </div>
      <div className="flex gap-2">
        <Button onClick={() => void router.invalidate()} className="rounded-lg">
          重试
        </Button>
        <Button variant="ghost" onClick={backToLogin} className="rounded-lg">
          退出登录
        </Button>
      </div>
    </div>
  );
}
