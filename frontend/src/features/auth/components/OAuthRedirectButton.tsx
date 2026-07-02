// input: OAuthProviderConfig, startOAuthRedirect(), shadcn Button, lucide Feather
// output: OAuthRedirectButton 组件 —— 白底 hairline 描边 squircle + 品牌色 logo 贴片，点按整页跳转飞书/Lark 授权页
// pos: auth feature - 飞书/Lark 登录按钮(授权码跳转流, 次级样式守 C5)；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
import { Feather } from 'lucide-react'

import { Button } from '@/components/ui/button'

import type { OAuthProviderConfig } from '../helpers/oauthProviders'
import { startOAuthRedirect } from '../helpers/oauthRedirect'

/** 品牌色 logo 贴片（飞书/Lark 同源产品，统一飞书蓝；品牌色仅限于此贴片，按钮主体守次级样式）。 */
function ProviderMark() {
  return (
    <span className="flex size-[18px] items-center justify-center rounded-[5px] bg-[#3370FF] text-white">
      <Feather className="size-3" strokeWidth={2} />
    </span>
  )
}

export function OAuthRedirectButton({ config }: { config: OAuthProviderConfig }) {
  return (
    <Button
      type="button"
      variant="outline"
      onClick={() => startOAuthRedirect(config)}
      className="border-line text-ink h-12 w-full gap-2.5 rounded-[10px] bg-white/60 text-sm font-medium shadow-none transition-all duration-300 ease-[cubic-bezier(0.32,0.72,0,1)] hover:bg-white active:scale-[0.99]"
    >
      <ProviderMark />
      {config.label}
    </Button>
  )
}
