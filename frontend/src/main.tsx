// input: #root DOM 节点, routeTree.gen(自动生成), index.css
// output: 前端应用入口(挂载 QueryClient + Router + Toaster)
// owner: wanhua.gu
// pos: 应用入口 - React 根挂载与全局 Provider；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'

import { GoogleOAuthProvider } from '@react-oauth/google'
import { QueryClientProvider } from '@tanstack/react-query'
import { createRouter, RouterProvider } from '@tanstack/react-router'
import { Toaster } from 'sonner'

import { queryClient } from '@/lib/queryClient'

import { routeTree } from './routeTree.gen'

// 自托管字体(替代 Google Fonts，去掉渲染阻塞的外链)：只导入实际使用的字族与字重——
// DESIGN.md 字重上限 600、src/ 内仅用到 font-medium(500)/font-semibold(600)；
// CJK 每档字重都是一大组 unicode-range 子集 CSS，多导一档就多一大块 bundle。
// 注意：Noto Sans SC 没有 600 静态字重，font-weight:600 的 CJK 会按规范向上回退到
// 700——所以 700 必须保留(它就是 CJK 的 semibold)，真正没人用的是 900。
// @fontsource/geist-sans 注册族名为 'Geist Sans'(index.css 的 --font-sans 已加该别名回退)；
// CJK 包按 unicode-range 分片，浏览器按需下载对应子集。fontsource 默认 font-display: swap。
import '@fontsource/geist-sans/400.css'
import '@fontsource/geist-sans/500.css'
import '@fontsource/geist-sans/600.css'
import '@fontsource/geist-mono/400.css'
import '@fontsource/geist-mono/500.css'
import '@fontsource/noto-sans-sc/400.css'
import '@fontsource/noto-sans-sc/500.css'
import '@fontsource/noto-serif-sc/500.css'
import '@fontsource/noto-serif-sc/600.css'
import '@fontsource/instrument-serif/400.css'
import '@fontsource/instrument-serif/400-italic.css'
import './index.css'

const router = createRouter({
  routeTree,
  defaultPreload: 'intent',
})

declare module '@tanstack/react-router' {
  interface Register {
    router: typeof router
  }
}

const rootElement = document.getElementById('root')
if (!rootElement) throw new Error('Root element #root not found')

const googleClientId = import.meta.env.VITE_GOOGLE_CLIENT_ID

const app = (
  <QueryClientProvider client={queryClient}>
    <RouterProvider router={router} />
    <Toaster position="top-center" richColors />
  </QueryClientProvider>
)

createRoot(rootElement).render(
  <StrictMode>
    {googleClientId ? (
      <GoogleOAuthProvider clientId={googleClientId}>{app}</GoogleOAuthProvider>
    ) : (
      app
    )}
  </StrictMode>,
)
