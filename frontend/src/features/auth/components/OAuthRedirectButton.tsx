// input: OAuthProviderConfig, startOAuthRedirect(), shadcn Button, lucide Feather
// output: OAuthRedirectButton 组件 —— 白底描边药丸 + 品牌色 logo 贴片，点按整页跳转飞书/Lark 授权页
// owner: wanhua.gu
// pos: auth feature - 飞书/Lark 登录按钮(授权码跳转流, 次级样式守 C5)；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
import { Feather } from 'lucide-react'

import { Button } from '@/components/ui/button'

import type { OAuthProviderConfig } from '../helpers/oauthProviders'
import { startOAuthRedirect } from '../helpers/oauthRedirect'

/** 品牌色 logo 贴片（飞书/Lark 同源产品，统一飞书蓝；品牌色仅限于此贴片，按钮主体守次级样式）。 */
function ProviderMark() {
  return (
    <span className="flex size-5 items-center justify-center rounded-md bg-[#3370FF] text-white">
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
      className="h-12 w-full gap-3 rounded-full border-border bg-card text-base font-medium transition-all duration-300 ease-[cubic-bezier(0.32,0.72,0,1)] hover:bg-muted active:scale-[0.985]"
    >
      <ProviderMark />
      {config.label}
    </Button>
  )
}
