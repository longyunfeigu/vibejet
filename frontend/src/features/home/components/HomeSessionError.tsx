// input: authStore.clearSession, TanStack navigate
// output: HomeSessionError —— 首页会话错误态
// owner: wanhua.gu
// pos: home feature - 首页错误态；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
import { useNavigate } from '@tanstack/react-router';

import { Button } from '@/components/ui/button';
import { clearSession } from '@/lib/authStore';

export function HomeSessionError() {
  const navigate = useNavigate();

  function backToLogin() {
    clearSession();
    void navigate({ to: '/login' });
  }

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
