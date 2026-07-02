// input: TanStack Router
// output: 根路由(根布局 Outlet)
// owner: wanhua.gu
// pos: 路由 - 根路由布局；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
import { createRootRoute, Outlet } from '@tanstack/react-router'

export const Route = createRootRoute({
  component: () => <Outlet />,
})
