// input: Vite 注入的 import.meta.env (VITE_API_URL 等)
// output: 前端全局类型声明（import.meta.env / VITE_API_URL 类型）
// owner: wanhua.gu
// pos: 类型声明 - Vite 客户端类型；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_URL: string
  readonly VITE_GOOGLE_CLIENT_ID?: string
  // 飞书登录：填 App ID 后登录页出现「使用飞书继续」（留空则隐藏）；URL/redirect 可选覆盖默认值
  readonly VITE_FEISHU_APP_ID?: string
  readonly VITE_FEISHU_AUTHORIZE_URL?: string
  readonly VITE_FEISHU_REDIRECT_URI?: string
  // Lark 国际登录：同飞书
  readonly VITE_LARK_APP_ID?: string
  readonly VITE_LARK_AUTHORIZE_URL?: string
  readonly VITE_LARK_REDIRECT_URI?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
