// input: authStore.getSession(), LoginScreen
// output: /login 路由(公开；已登录则重定向到 /)
// owner: wanhua.gu
// pos: 路由 - 登录页；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
import { createFileRoute, redirect } from '@tanstack/react-router'

import { LoginScreen } from '@/features/auth'
import { getSession } from '@/lib/authStore'

export const Route = createFileRoute('/login/')({
  beforeLoad: () => {
    if (getSession()) {
      throw redirect({ to: '/' })
    }
  },
  component: LoginScreen,
})
