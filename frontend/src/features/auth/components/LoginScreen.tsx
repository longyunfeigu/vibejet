// input: LoginForm, BrandPanel, GoogleSignInButton, OAuthRedirectButton, getConfiguredOAuthProviders
// output: LoginScreen 组件 —— 编辑艺术风分栏登录屏（左纸色衬线排印认证列 / 右画廊式装裱画）
// pos: auth feature - 登录页整屏布局(front-of-house, 纸/墨/松绿 token 系)；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
import { getConfiguredOAuthProviders } from '../helpers/oauthProviders'
import { BrandPanel } from './BrandPanel'
import { GoogleSignInButton } from './GoogleSignInButton'
import { LoginForm } from './LoginForm'
import { OAuthRedirectButton } from './OAuthRedirectButton'

const googleEnabled = Boolean(import.meta.env.VITE_GOOGLE_CLIENT_ID)

export function LoginScreen() {
  const oauthProviders = getConfiguredOAuthProviders()
  const socialEnabled = googleEnabled || oauthProviders.length > 0

  return (
    <div className="bg-paper text-ink flex min-h-[100dvh]">
      {/* 左：认证列（纸色底 + 衬线排印） */}
      <div className="flex w-full flex-col px-6 sm:px-12 lg:w-[46%] xl:px-20">
        <div className="animate-fade-up flex w-full flex-1 flex-col">
          <header className="pt-12">
            <span className="font-display text-[26px] italic leading-none">vibejet</span>
          </header>

          <main className="my-auto w-full max-w-[360px] py-14">
            <h1 className="font-serif text-[40px] font-semibold leading-tight tracking-[0.01em]">
              欢迎回来。
            </h1>
            <p className="text-ink-muted mt-3.5 text-[15px] leading-relaxed">
              登录以继续你的构建。
            </p>

            {socialEnabled && (
              <>
                <div className="mt-11 flex flex-col gap-3">
                  {googleEnabled && <GoogleSignInButton />}
                  {oauthProviders.map((p) => (
                    <OAuthRedirectButton key={p.provider} config={p} />
                  ))}
                </div>
                <div className="text-ink-faint my-8 flex items-center gap-4 text-xs tracking-[0.32em]">
                  <span className="bg-line-soft h-px flex-1" />
                  或
                  <span className="bg-line-soft h-px flex-1" />
                </div>
              </>
            )}

            <div className={socialEnabled ? undefined : 'mt-12'}>
              <LoginForm />
            </div>

            <div className="text-ink-muted mt-6 flex items-baseline justify-between text-[13.5px]">
              <span>
                还没有账号？{' '}
                <a
                  href="#"
                  className="border-line text-pine hover:border-pine border-b pb-px transition-colors"
                >
                  注册
                </a>
              </span>
              <a
                href="#"
                className="border-line text-pine hover:border-pine border-b pb-px transition-colors"
              >
                忘记密码
              </a>
            </div>
          </main>

          <footer className="pb-10">
            <p className="text-ink-ghost text-xs tracking-[0.04em]">
              © vibejet 2026 ·{' '}
              <a href="#" className="hover:text-ink transition-colors">
                条款
              </a>{' '}
              ·{' '}
              <a href="#" className="hover:text-ink transition-colors">
                隐私
              </a>
            </p>
          </footer>
        </div>
      </div>

      {/* 右：画廊面板（移动端隐藏） */}
      <BrandPanel />
    </div>
  )
}
