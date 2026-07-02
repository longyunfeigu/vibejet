// input: showcaseColumns/showcaseToneClass, marquee 动效(index.css)
// output: ShowcaseCollage 组件 —— 登录页右侧倾斜滚动的"产品屏"卡片墙
// owner: wanhua.gu
// pos: auth feature - 登录页右侧视觉锚(纯装饰，非语义 UI)；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
import type { CSSProperties } from 'react';

import {
  showcaseColumns,
  showcaseToneClass,
  type ShowcaseCardSpec,
} from '../helpers/showcaseCards';
import { cn } from '@/lib/utils';

function Shell({ children }: { children: React.ReactNode }) {
  return (
    <div className="mb-5 w-52 overflow-hidden rounded-3xl bg-card shadow-2xl ring-1 ring-border/70">
      {children}
    </div>
  );
}

function ScreenCard({ spec }: { spec: ShowcaseCardSpec }) {
  const tone = showcaseToneClass[spec.tone];

  if (spec.variant === 'hero') {
    const Icon = spec.icon;
    return (
      <Shell>
        <div className={cn('relative h-28 bg-gradient-to-br', tone.gradient)}>
          <span className="absolute left-4 top-4 flex size-9 items-center justify-center rounded-xl bg-white/25 text-white backdrop-blur-sm">
            <Icon className="size-5" strokeWidth={1.5} />
          </span>
          <span className="absolute right-4 top-4 size-2 rounded-full bg-white/60" />
        </div>
        <div className="flex flex-col gap-2 p-4">
          <p className="text-[12px] font-semibold text-neutral-900">{spec.title}</p>
          <p className="text-[10px] leading-relaxed text-neutral-400">{spec.sub}</p>
        </div>
      </Shell>
    );
  }
  if (spec.variant === 'stat') {
    const Icon = spec.icon;
    return (
      <Shell>
        <div className="flex flex-col gap-3 p-4">
          <div className="flex items-center gap-2">
            <span className={cn('flex size-7 items-center justify-center rounded-lg', tone.soft)}>
              <Icon className="size-4" strokeWidth={1.5} />
            </span>
            <span className="text-[11px] font-medium text-neutral-500">{spec.label}</span>
          </div>
          <div className="text-2xl font-bold tracking-tight text-neutral-900">{spec.value}</div>
          <div className="flex h-12 items-end gap-1.5">
            {spec.bars.map((h, i) => (
              <div
                key={i}
                className={cn(
                  'flex-1 rounded-sm',
                  i === spec.bars.length - 1 ? tone.solid : 'bg-neutral-200',
                )}
                style={{ height: `${h}%` }}
              />
            ))}
          </div>
        </div>
      </Shell>
    );
  }
  if (spec.variant === 'chat') {
    const Icon = spec.icon;
    return (
      <Shell>
        <div className="flex flex-col gap-2.5 p-4">
          <div className="flex items-center gap-2">
            <span className={cn('flex size-7 items-center justify-center rounded-full', tone.soft)}>
              <Icon className="size-4" strokeWidth={1.5} />
            </span>
            <span className="text-[11px] font-medium text-neutral-500">{spec.title}</span>
          </div>
          <div className="max-w-[82%] rounded-2xl rounded-tl-sm bg-neutral-100 px-3 py-2 text-[10px] text-neutral-600">
            {spec.ask}
          </div>
          <div
            className={cn(
              'ml-auto max-w-[82%] rounded-2xl rounded-tr-sm bg-gradient-to-br px-3 py-2 text-[10px] text-white',
              tone.gradient,
            )}
          >
            {spec.reply}
          </div>
        </div>
      </Shell>
    );
  }
  const Icon = spec.icon;
  return (
    <Shell>
      <div
        className={cn(
          'flex items-center gap-2 bg-gradient-to-br px-4 py-3 text-white',
          tone.gradient,
        )}
      >
        <Icon className="size-4" strokeWidth={1.5} />
        <span className="text-[11px] font-semibold">{spec.title}</span>
      </div>
      <div className="flex flex-col gap-3 p-4">
        {Array.from({ length: spec.rows }).map((_, i) => (
          <div key={i} className="flex items-center gap-2.5">
            <span className="size-6 shrink-0 rounded-full bg-neutral-200" />
            <div className="flex flex-1 flex-col gap-1">
              <span className="h-2 w-2/3 rounded-full bg-neutral-200" />
              <span className="h-1.5 w-1/2 rounded-full bg-neutral-100" />
            </div>
            <span className={cn('size-2 shrink-0 rounded-full', tone.solid)} />
          </div>
        ))}
      </div>
    </Shell>
  );
}

function Column({
  specs,
  duration,
  reverse,
}: {
  specs: ShowcaseCardSpec[];
  duration: string;
  reverse?: boolean;
}) {
  return (
    <div className="w-[208px] shrink-0">
      <div
        className={cn(
          'animate-marquee-y flex flex-col',
          reverse && '[animation-direction:reverse]',
        )}
        style={{ '--marquee-duration': duration } as CSSProperties}
      >
        {specs.map((s, i) => (
          <ScreenCard key={`a${i}`} spec={s} />
        ))}
        {specs.map((s, i) => (
          <ScreenCard key={`b${i}`} spec={s} />
        ))}
      </div>
    </div>
  );
}

export function ShowcaseCollage() {
  return (
    <div className="relative hidden overflow-hidden bg-foreground lg:block">
      <div className="absolute left-1/2 top-1/2 flex gap-5 [transform:translate(-50%,-50%)_rotate(-16deg)_scale(1.5)]">
        <Column specs={showcaseColumns[0]} duration="56s" />
        <Column specs={showcaseColumns[1]} duration="46s" reverse />
        <Column specs={showcaseColumns[2]} duration="64s" />
      </div>
      <div className="pointer-events-none absolute inset-0 bg-gradient-to-br from-indigo-600/25 via-transparent to-fuchsia-600/30 mix-blend-soft-light" />
      <div className="pointer-events-none absolute inset-0 bg-foreground/25" />
    </div>
  );
}
