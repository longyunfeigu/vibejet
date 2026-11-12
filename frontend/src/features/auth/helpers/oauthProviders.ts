export type OAuthProviderId = 'feishu' | 'lark';

export interface OAuthProviderConfig {
  provider: OAuthProviderId;
  label: string;
  appId: string;
  authorizeUrl: string;
  redirectUri: string;
}

// 授权页默认端点（可被 env 覆盖）：飞书国内 / Lark 国际不同域名。
const DEFAULT_AUTHORIZE_URLS: Record<OAuthProviderId, string> = {
  feishu: 'https://accounts.feishu.cn/open-apis/authen/v1/authorize',
  lark: 'https://accounts.larksuite.com/open-apis/authen/v1/authorize',
};

const LABELS: Record<OAuthProviderId, string> = {
  feishu: '使用飞书继续',
  lark: '使用 Lark 继续',
};

// 默认回调地址：须与后端 {provider}_OAUTH_REDIRECT_URI 及开放平台控制台注册值一致。
function defaultRedirectUri(): string {
  return `${window.location.origin}/auth/callback`;
}

export function getConfiguredOAuthProviders(): OAuthProviderConfig[] {
  const env = import.meta.env;
  const configs: OAuthProviderConfig[] = [];

  if (env.VITE_FEISHU_APP_ID) {
    configs.push({
      provider: 'feishu',
      label: LABELS.feishu,
      appId: env.VITE_FEISHU_APP_ID,
      authorizeUrl: env.VITE_FEISHU_AUTHORIZE_URL ?? DEFAULT_AUTHORIZE_URLS.feishu,
      redirectUri: env.VITE_FEISHU_REDIRECT_URI ?? defaultRedirectUri(),
    });
  }
  if (env.VITE_LARK_APP_ID) {
    configs.push({
      provider: 'lark',
      label: LABELS.lark,
      appId: env.VITE_LARK_APP_ID,
      authorizeUrl: env.VITE_LARK_AUTHORIZE_URL ?? DEFAULT_AUTHORIZE_URLS.lark,
      redirectUri: env.VITE_LARK_REDIRECT_URI ?? defaultRedirectUri(),
    });
  }
  return configs;
}
