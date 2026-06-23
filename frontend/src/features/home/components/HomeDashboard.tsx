// input: useCurrentUser, AppShell, authStore.clearSession
// output: HomeDashboard —— 已登录首页总览
// owner: wanhua.gu
// pos: home feature - 首页仪表盘内容；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
import { useNavigate } from '@tanstack/react-router';
import { ArrowUpRight, CheckCircle2, Clock3, Rocket, ShieldCheck } from 'lucide-react';

import { AppShell } from '@/components/layout';
import { Button } from '@/components/ui/button';
import { clearSession } from '@/lib/authStore';
import { cn } from '@/lib/utils';

import { useCurrentUser } from '../hooks/useCurrentUser';
import type { HomeActivity, HomeMetric } from '../types';

const metrics: HomeMetric[] = [
  { label: '活跃项目', value: '8', helper: '2 个等待发布' },
  { label: '本周部署', value: '24', helper: '成功率 99.9%' },
  { label: '平均响应', value: '42ms', helper: '较上周快 18%' },
];

const activities: HomeActivity[] = [
  { title: '生产环境部署完成', detail: 'website-main · 38 秒前', state: 'success' },
  { title: '安全扫描等待复核', detail: 'api-gateway · 12 分钟前', state: 'warning' },
  { title: '预览环境已生成', detail: 'checkout-redesign · 26 分钟前', state: 'neutral' },
];

const stateClass: Record<HomeActivity['state'], string> = {
  success: 'bg-success',
  warning: 'bg-warning',
  neutral: 'bg-muted-foreground',
};

function HomeHero({ name }: { name: string }) {
  return (
    <section className="border-border bg-card grid gap-6 rounded-xl border p-6 shadow-sm lg:grid-cols-[1fr_auto] lg:items-center">
      <div className="flex max-w-2xl flex-col gap-3">
        <div className="text-muted-foreground flex items-center gap-2 text-sm">
          <ShieldCheck className="size-4" strokeWidth={1.5} />
          工作台已连接
        </div>
        <div className="flex flex-col gap-2">
          <h1 className="text-3xl font-semibold tracking-tight">你好，{name}</h1>
          <p className="text-muted-foreground leading-relaxed">
            从这里继续管理项目、部署和质量门禁。关键状态会优先浮到首页，减少来回切换。
          </p>
        </div>
      </div>
      <div className="flex flex-wrap gap-3">
        <Button className="rounded-lg">
          <Rocket className="size-4" strokeWidth={1.5} />
          新建项目
        </Button>
        <Button variant="outline" className="rounded-lg">
          查看部署
          <ArrowUpRight className="size-4" strokeWidth={1.5} />
        </Button>
      </div>
    </section>
  );
}

function MetricGrid() {
  return (
    <section className="grid gap-4 md:grid-cols-3">
      {metrics.map((metric) => (
        <div key={metric.label} className="border-border bg-card rounded-xl border p-5 shadow-sm">
          <p className="text-muted-foreground text-sm">{metric.label}</p>
          <div className="mt-3 flex items-end justify-between gap-3">
            <p className="font-mono text-3xl font-semibold tracking-tight">{metric.value}</p>
            <p className="text-muted-foreground text-right text-xs">{metric.helper}</p>
          </div>
        </div>
      ))}
    </section>
  );
}

function ActivityPanel() {
  return (
    <section className="border-border bg-card rounded-xl border p-5 shadow-sm">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h2 className="text-base font-semibold">最近动态</h2>
          <p className="text-muted-foreground mt-1 text-sm">部署、扫描和预览环境的最新状态。</p>
        </div>
        <Clock3 className="text-muted-foreground size-5" strokeWidth={1.5} />
      </div>
      <div className="mt-5 divide-y">
        {activities.map((activity) => (
          <div key={activity.title} className="flex items-start gap-3 py-4 first:pt-0 last:pb-0">
            <span
              className={cn('mt-1 size-2.5 shrink-0 rounded-full', stateClass[activity.state])}
            />
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium" title={activity.title}>
                {activity.title}
              </p>
              <p className="text-muted-foreground mt-1 truncate text-sm" title={activity.detail}>
                {activity.detail}
              </p>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

function ReadinessPanel() {
  return (
    <section className="border-border bg-card rounded-xl border p-5 shadow-sm">
      <div className="flex items-center gap-3">
        <span className="bg-success/10 text-success flex size-10 items-center justify-center rounded-xl">
          <CheckCircle2 className="size-5" strokeWidth={1.5} />
        </span>
        <div>
          <h2 className="text-base font-semibold">质量门禁</h2>
          <p className="text-muted-foreground mt-1 text-sm">主分支当前可发布。</p>
        </div>
      </div>
      <div className="mt-5 grid gap-3 text-sm">
        {['类型检查通过', '接口健康检查通过', '最近一次部署成功'].map((item) => (
          <div key={item} className="bg-muted/60 flex items-center gap-2 rounded-lg px-3 py-2">
            <CheckCircle2 className="text-success size-4" strokeWidth={1.5} />
            <span>{item}</span>
          </div>
        ))}
      </div>
    </section>
  );
}

export function HomeDashboard() {
  const { data: user } = useCurrentUser();
  const navigate = useNavigate();
  const displayName = user.fullName ?? user.username;

  function handleLogout() {
    clearSession();
    void navigate({ to: '/login' });
  }

  return (
    <AppShell currentUser={user} onLogout={handleLogout}>
      <HomeHero name={displayName} />
      <MetricGrid />
      <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_360px]">
        <ActivityPanel />
        <ReadinessPanel />
      </div>
    </AppShell>
  );
}
