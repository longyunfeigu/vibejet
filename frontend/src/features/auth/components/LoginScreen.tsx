// input: LoginForm, ShowcaseCollage 组件
// output: LoginScreen 组件 —— 左居中认证面板 / 右倾斜产品屏卡片墙 的分栏登录屏
// owner: wanhua.gu
// pos: auth feature - 登录页整屏布局(front-of-house, 对齐 Mobbin 工艺)；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
import { Sparkles } from 'lucide-react'

import { GoogleSignInButton } from './GoogleSignInButton'
import { LoginForm } from './LoginForm'
import { ShowcaseCollage } from './ShowcaseCollage'

const googleEnabled = Boolean(import.meta.env.VITE_GOOGLE_CLIENT_ID)

export function LoginScreen() {
  return (
    <div className="grid min-h-[100dvh] lg:grid-cols-2">
      {/* 左：认证面板（整体居中） */}
      <div className="flex items-center justify-center px-6 py-12 sm:px-10">
        <div className="animate-fade-up flex w-full max-w-sm flex-col items-center gap-8 text-center">
          {/* wordmark */}
          <div className="flex items-center gap-2.5">
            <span className="flex size-9 items-center justify-center rounded-xl bg-gradient-to-br from-brand-from via-brand-via to-brand-to text-white shadow-[0_6px_16px_rgba(80,70,229,0.4)]">
              <Sparkles className="size-5" strokeWidth={1.5} />
            </span>
            <span className="text-lg font-semibold tracking-tight">vibejet</span>
          </div>

          {/* heading */}
          <div className="flex flex-col gap-2.5">
            <h1 className="text-[2.25rem] font-black leading-[1.15] tracking-tight">欢迎回来</h1>
            <p className="text-muted-foreground text-[15px] leading-relaxed">
              登录 vibejet，继续把想法更快地变成线上产品。
            </p>
          </div>

          {/* form area：有 Google 配置时先显示 Google 按钮 + 分隔线 */}
          <div className="flex w-full flex-col gap-5">
            {googleEnabled && (
              <>
                <div className="flex justify-center">
                  <GoogleSignInButton />
                </div>
                <div className="text-muted-foreground/70 flex items-center gap-3">
                  <span className="bg-border h-px flex-1" />
                  <span className="text-xs">或</span>
                  <span className="bg-border h-px flex-1" />
                </div>
              </>
            )}
            <LoginForm />
          </div>

          {/* footer */}
          <div className="flex flex-col gap-4">
            <p className="text-muted-foreground text-sm">
              还没有账号？
              <a href="#" className="text-foreground font-semibold underline-offset-4 hover:underline">
                注册
              </a>
            </p>
            <p className="text-muted-foreground/80 text-xs leading-relaxed">
              继续即代表你同意我们的
              <a href="#" className="hover:text-foreground underline underline-offset-2">
                服务条款
              </a>
              与
              <a href="#" className="hover:text-foreground underline underline-offset-2">
                隐私政策
              </a>
              。
            </p>
          </div>
        </div>
      </div>

      {/* 右：产品屏卡片墙（移动端隐藏） */}
      <ShowcaseCollage />
    </div>
  )
}
