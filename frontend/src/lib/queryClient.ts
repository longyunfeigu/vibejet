// input: @tanstack/react-query
// output: queryClient —— 全局共享的 QueryClient 单例(供 main.tsx 挂载 + 登出清缓存复用)
// owner: wanhua.gu
// pos: 跨域基础设施 - React Query 客户端单例；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
import { QueryClient } from '@tanstack/react-query'

// 单一实例：main.tsx 用它挂 Provider，authStore.clearSession 登出时 clear() 同一份缓存，
// 避免换用户后旧用户 profile 仍从 staleTime 内的缓存命中。
// 不在此 import authStore，保持无环依赖(authStore -> queryClient 单向)。
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
})
