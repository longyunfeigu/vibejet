// input: Radix 原语 + cn() (@/lib/utils)
// output: Skeleton 骨架占位组件
// owner: wanhua.gu
// pos: shadcn UI 组件 - 骨架屏（vendored，可改）；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
import { cn } from "@/lib/utils"

function Skeleton({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="skeleton"
      className={cn("animate-pulse rounded-md bg-accent", className)}
      {...props}
    />
  )
}

export { Skeleton }
