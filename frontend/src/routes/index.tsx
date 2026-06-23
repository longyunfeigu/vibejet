// input: authStore.getSession, HomePage, HomeSessionError
// output: / 路由(未登录重定向到 /login，已登录挂载 home feature)
// owner: wanhua.gu
// pos: 路由 - 首页守卫与 feature 挂载；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
import { createFileRoute, redirect } from '@tanstack/react-router';

import { HomePage, HomeSessionError } from '@/features/home';
import { getSession } from '@/lib/authStore';

export const Route = createFileRoute('/')({
  beforeLoad: () => {
    if (!getSession()) {
      throw redirect({ to: '/login' });
    }
  },
  component: HomePage,
  errorComponent: HomeSessionError,
});
