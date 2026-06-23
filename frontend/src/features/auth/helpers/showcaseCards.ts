// input: lucide 图标
// output: 登录展示墙卡片数据与色调 class 映射
// owner: wanhua.gu
// pos: auth feature - 登录页装饰性 mock 展示配置；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
import {
  Activity,
  BarChart3,
  Bot,
  CheckCircle2,
  GitBranch,
  type LucideIcon,
  Rocket,
  TrendingUp,
  Users,
} from 'lucide-react';

export type ShowcaseTone = 'indigo' | 'violet' | 'amber' | 'emerald' | 'rose' | 'sky';

export type ShowcaseCardSpec =
  | { variant: 'hero'; tone: ShowcaseTone; icon: LucideIcon; title: string; sub: string }
  | {
      variant: 'stat';
      tone: ShowcaseTone;
      icon: LucideIcon;
      label: string;
      value: string;
      bars: number[];
    }
  | {
      variant: 'chat';
      tone: ShowcaseTone;
      icon: LucideIcon;
      title: string;
      ask: string;
      reply: string;
    }
  | { variant: 'list'; tone: ShowcaseTone; icon: LucideIcon; title: string; rows: number };

export const showcaseToneClass: Record<
  ShowcaseTone,
  { gradient: string; soft: string; solid: string }
> = {
  indigo: {
    gradient: 'from-indigo-500 to-violet-600',
    soft: 'bg-indigo-100 text-indigo-600',
    solid: 'bg-indigo-500',
  },
  violet: {
    gradient: 'from-violet-500 to-fuchsia-500',
    soft: 'bg-violet-100 text-violet-600',
    solid: 'bg-violet-500',
  },
  amber: {
    gradient: 'from-amber-400 to-orange-500',
    soft: 'bg-amber-100 text-amber-600',
    solid: 'bg-amber-500',
  },
  emerald: {
    gradient: 'from-emerald-400 to-teal-500',
    soft: 'bg-emerald-100 text-emerald-600',
    solid: 'bg-emerald-500',
  },
  rose: {
    gradient: 'from-rose-400 to-pink-500',
    soft: 'bg-rose-100 text-rose-600',
    solid: 'bg-rose-500',
  },
  sky: {
    gradient: 'from-sky-400 to-blue-500',
    soft: 'bg-sky-100 text-sky-600',
    solid: 'bg-sky-500',
  },
};

export const showcaseColumns: ShowcaseCardSpec[][] = [
  [
    {
      variant: 'chat',
      tone: 'indigo',
      icon: Bot,
      title: 'vibejet 助手',
      ask: '帮我把这个分支部署到生产',
      reply: '已部署，用时 38s',
    },
    {
      variant: 'stat',
      tone: 'emerald',
      icon: TrendingUp,
      label: '本月活跃',
      value: '12.8k',
      bars: [40, 55, 48, 70, 62, 88],
    },
    {
      variant: 'hero',
      tone: 'amber',
      icon: Rocket,
      title: '一键发布',
      sub: '从想法到上线，平均 4 分钟。',
    },
    { variant: 'list', tone: 'sky', icon: Users, title: '团队成员', rows: 3 },
    {
      variant: 'stat',
      tone: 'violet',
      icon: BarChart3,
      label: '请求量',
      value: '2.4M',
      bars: [30, 50, 44, 60, 75, 92],
    },
  ],
  [
    { variant: 'list', tone: 'rose', icon: Activity, title: '实时活动', rows: 4 },
    {
      variant: 'hero',
      tone: 'indigo',
      icon: GitBranch,
      title: '分支预览',
      sub: '每个 PR 自动生成可访问的预览环境。',
    },
    {
      variant: 'stat',
      tone: 'amber',
      icon: TrendingUp,
      label: '部署成功率',
      value: '99.9%',
      bars: [70, 80, 76, 88, 84, 96],
    },
    {
      variant: 'chat',
      tone: 'violet',
      icon: Bot,
      title: '智能补全',
      ask: '这段代码有什么风险？',
      reply: '已标注 2 处并发问题',
    },
    {
      variant: 'hero',
      tone: 'emerald',
      icon: CheckCircle2,
      title: '质量门禁',
      sub: '测试、审查、安全扫描全通过。',
    },
  ],
  [
    {
      variant: 'stat',
      tone: 'sky',
      icon: BarChart3,
      label: '响应延迟',
      value: '42ms',
      bars: [60, 45, 52, 38, 30, 24],
    },
    {
      variant: 'hero',
      tone: 'rose',
      icon: Rocket,
      title: '全球加速',
      sub: '边缘网络覆盖 200+ 城市节点。',
    },
    {
      variant: 'chat',
      tone: 'emerald',
      icon: Bot,
      title: 'vibejet 助手',
      ask: '总结今天的变更',
      reply: '6 次提交，3 个 PR 已合并',
    },
    { variant: 'list', tone: 'indigo', icon: Users, title: '协作动态', rows: 3 },
    {
      variant: 'stat',
      tone: 'violet',
      icon: TrendingUp,
      label: '转化率',
      value: '7.3%',
      bars: [35, 48, 55, 50, 68, 80],
    },
  ],
];
