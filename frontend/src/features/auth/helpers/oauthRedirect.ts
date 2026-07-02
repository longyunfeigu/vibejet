// input: OAuthProviderConfig, sessionStorage, window.crypto, window.location
// output: startOAuthRedirect(config) 发起整页跳转授权; takeStoredOAuthState() 取并清空已存 state（防 CSRF 单次使用）
// owner: wanhua.gu
// pos: auth feature - 飞书/Lark 授权码跳转流（拼授权 URL + state 防 CSRF）；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
import type { OAuthProviderConfig } from './oauthProviders'

const STATE_KEY = 'vibejet.oauth_state'

function randomNonce(): string {
  // 现代浏览器均有 crypto.randomUUID；回退到时间+随机串。
  if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) {
    return crypto.randomUUID()
  }
  return `${Date.now()}-${Math.random().toString(36).slice(2)}`
}

/** 发起授权：state = `{provider}:{nonce}` 存 sessionStorage，整页跳转到授权页。 */
export function startOAuthRedirect(config: OAuthProviderConfig): void {
  const state = `${config.provider}:${randomNonce()}`
  sessionStorage.setItem(STATE_KEY, state)

  const url = new URL(config.authorizeUrl)
  url.searchParams.set('client_id', config.appId)
  url.searchParams.set('redirect_uri', config.redirectUri)
  url.searchParams.set('response_type', 'code')
  url.searchParams.set('state', state)
  window.location.assign(url.toString())
}

/** 取出并清空已存 state（单次使用，防重放）；回调页据此做 CSRF 校验。 */
export function takeStoredOAuthState(): string | null {
  const stored = sessionStorage.getItem(STATE_KEY)
  if (stored) sessionStorage.removeItem(STATE_KEY)
  return stored
}
