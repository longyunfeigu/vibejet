// input: authStore via OAuthCallbackScreen, 回调 query(code,state)
// output: /auth/callback 路由（公开；校验 search 后渲染回调屏）
// owner: wanhua.gu
// pos: 路由 - 飞书/Lark 授权码回调页（薄路由，编排在 OAuthCallbackScreen）；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
import { createFileRoute } from '@tanstack/react-router'

import { OAuthCallbackScreen } from '@/features/auth'

interface CallbackSearch {
  code?: string
  state?: string
}

export const Route = createFileRoute('/auth/callback')({
  validateSearch: (search: Record<string, unknown>): CallbackSearch => ({
    code: typeof search.code === 'string' ? search.code : undefined,
    state: typeof search.state === 'string' ? search.state : undefined,
  }),
  component: OAuthCallbackScreen,
})
