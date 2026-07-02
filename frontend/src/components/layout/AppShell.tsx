// input: currentUser, onLogout, children
// output: AppShell —— 已登录区域的应用外壳
// owner: wanhua.gu
// pos: 跨域布局组件 - 顶栏/侧栏/内容壳；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
import type { ReactNode } from 'react';

import { Bell, LogOut, Sparkles } from 'lucide-react';

import { Button } from '@/components/ui/button';
import type { CurrentUser } from '@/features/auth';
import { cn } from '@/lib/utils';

interface AppShellProps {
  currentUser: CurrentUser;
  children: ReactNode;
  onLogout: () => void;
}

const navItems = [
  { label: '总览', active: true },
  { label: '项目', active: false },
  { label: '部署', active: false },
  { label: '设置', active: false },
];

function getDisplayName(user: CurrentUser): string {
  return user.fullName ?? user.username;
}

export function AppShell({ currentUser, children, onLogout }: AppShellProps) {
  const displayName = getDisplayName(currentUser);

  return (
    <div className="bg-background text-foreground min-h-[100dvh]">
      <div className="border-border bg-card/80 sticky top-0 z-10 border-b backdrop-blur-xl">
        <div className="mx-auto flex h-16 max-w-7xl items-center justify-between gap-4 px-4 sm:px-6 lg:px-8">
          <div className="flex min-w-0 items-center gap-8">
            <div className="flex shrink-0 items-center gap-2.5">
              <span className="from-brand-from via-brand-via to-brand-to flex size-9 items-center justify-center rounded-xl bg-gradient-to-br text-white shadow-sm">
                <Sparkles className="size-5" strokeWidth={1.5} />
              </span>
              <span className="text-base font-semibold tracking-tight">vibejet</span>
            </div>
            <nav className="hidden items-center gap-1 md:flex" aria-label="主导航">
              {navItems.map((item) => (
                <button
                  key={item.label}
                  type="button"
                  disabled={!item.active}
                  aria-current={item.active ? 'page' : undefined}
                  className={cn(
                    'rounded-lg px-3 py-2 text-sm font-medium transition-colors',
                    item.active
                      ? 'bg-muted text-foreground'
                      : 'text-muted-foreground/70 cursor-not-allowed',
                  )}
                >
                  {item.label}
                </button>
              ))}
            </nav>
          </div>

          <div className="flex min-w-0 items-center gap-2">
            <Button
              variant="ghost"
              size="icon"
              aria-label="通知"
              className="hidden rounded-lg sm:inline-flex"
            >
              <Bell className="size-4" strokeWidth={1.5} />
            </Button>
            <div className="border-border hidden min-w-0 items-center gap-3 border-l pl-4 sm:flex">
              <div className="bg-muted text-muted-foreground flex size-9 shrink-0 items-center justify-center rounded-full text-sm font-semibold">
                {displayName.slice(0, 1).toUpperCase()}
              </div>
              <div className="min-w-0">
                <p className="truncate text-sm font-medium">{displayName}</p>
                <p className="text-muted-foreground truncate text-xs">{currentUser.email}</p>
              </div>
            </div>
            <Button variant="outline" onClick={onLogout} className="rounded-lg">
              <LogOut className="size-4" strokeWidth={1.5} />
              <span className="hidden sm:inline">退出</span>
            </Button>
          </div>
        </div>
      </div>

      <main className="mx-auto flex max-w-7xl flex-col gap-6 px-4 py-6 sm:px-6 lg:px-8">
        {children}
      </main>
    </div>
  );
}
