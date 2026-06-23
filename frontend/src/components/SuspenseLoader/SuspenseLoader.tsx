// input: children(异步内容) + 可选 fallback
// output: SuspenseLoader 组件 —— 用 Skeleton 兜底的 Suspense 包装
// owner: wanhua.gu
// pos: 跨域共享组件 - Suspense 加载兜底；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
import { Suspense, type ReactNode } from 'react'

import { Skeleton } from '@/components/ui/skeleton'

interface SuspenseLoaderProps {
  children: ReactNode
  fallback?: ReactNode
}

function DefaultFallback() {
  return (
    <div className="flex w-full max-w-sm flex-col gap-3">
      <Skeleton className="h-8 w-1/2" />
      <Skeleton className="h-4 w-3/4" />
      <Skeleton className="h-4 w-2/3" />
    </div>
  )
}

export function SuspenseLoader({ children, fallback }: SuspenseLoaderProps) {
  return <Suspense fallback={fallback ?? <DefaultFallback />}>{children}</Suspense>
}
