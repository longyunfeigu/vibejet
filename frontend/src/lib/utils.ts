// input: clsx, tailwind-merge
// output: cn(...inputs) —— 合并并去重 Tailwind class 的工具(clsx + tailwind-merge)
// owner: wanhua.gu
// pos: 跨域样式工具 - className 合并；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}
