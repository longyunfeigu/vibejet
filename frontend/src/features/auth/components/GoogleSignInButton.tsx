// input: useGoogleAuth() hook（授权码流）, shadcn Button
// output: GoogleSignInButton 组件 —— 白底 hairline 描边 squircle + 官方四色 G logo，点按触发 Google 授权码 popup
// pos: auth feature - Google 登录按钮(授权码流, 次级样式守 C5)；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
import { Loader2 } from 'lucide-react'

import { Button } from '@/components/ui/button'

import { useGoogleAuth } from '../hooks/useGoogleLogin'

/** Google 官方四色 “G” 标志（内联 SVG，避免额外依赖/网络资源）。 */
function GoogleIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" aria-hidden="true">
      <path
        fill="#4285F4"
        d="M23.52 12.27c0-.82-.07-1.6-.21-2.36H12v4.46h6.46a5.52 5.52 0 0 1-2.4 3.62v3h3.88c2.27-2.09 3.58-5.17 3.58-8.72z"
      />
      <path
        fill="#34A853"
        d="M12 24c3.24 0 5.96-1.08 7.94-2.9l-3.88-3a7.2 7.2 0 0 1-4.06 1.16 7.14 7.14 0 0 1-6.71-4.94H1.28v3.1A12 12 0 0 0 12 24z"
      />
      <path
        fill="#FBBC05"
        d="M5.29 14.32a7.2 7.2 0 0 1 0-4.63v-3.1H1.28a12 12 0 0 0 0 10.83l4.01-3.1z"
      />
      <path
        fill="#EA4335"
        d="M12 4.77c1.76 0 3.35.61 4.6 1.8l3.44-3.44A11.99 11.99 0 0 0 12 0 12 12 0 0 0 1.28 6.59l4.01 3.1A7.14 7.14 0 0 1 12 4.77z"
      />
    </svg>
  )
}

export function GoogleSignInButton() {
  const { login, isPending } = useGoogleAuth()

  return (
    <Button
      type="button"
      variant="outline"
      onClick={() => login()}
      disabled={isPending}
      className="border-line text-ink h-12 w-full gap-2.5 rounded-[10px] bg-white/60 text-sm font-medium shadow-none transition-all duration-300 ease-[cubic-bezier(0.32,0.72,0,1)] hover:bg-white active:scale-[0.99]"
    >
      {isPending ? (
        <Loader2 className="size-[18px] animate-spin" strokeWidth={1.5} />
      ) : (
        <GoogleIcon className="size-[18px]" />
      )}
      使用 Google 继续
    </Button>
  )
}
