// input: @react-oauth/google useGoogleLogin(auth-code), authApi.loginWithGoogle, authStore.setSession, router navigate, sonner toast
// output: useGoogleAuth() —— { login, isPending }；触发 Google 授权码 popup，拿 code 发后端换 token
// owner: wanhua.gu
// pos: auth feature - Google 授权码登录用例编排 hook（popup → code → 后端交换 → 存会话+跳转）；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
import { useGoogleLogin } from '@react-oauth/google'
import { useMutation } from '@tanstack/react-query'
import { useNavigate } from '@tanstack/react-router'
import { toast } from 'sonner'

import { setSession } from '@/lib/authStore'

import { loginWithGoogle } from '../api/authApi'
import { extractAuthErrorMessage } from '../helpers/authError'

export interface UseGoogleAuthResult {
  login: () => void
  isPending: boolean
}

export function useGoogleAuth(): UseGoogleAuthResult {
  const navigate = useNavigate()

  const mutation = useMutation({
    mutationFn: (code: string) => loginWithGoogle(code),
    onSuccess: (tokens) => {
      setSession({ accessToken: tokens.accessToken, refreshToken: tokens.refreshToken })
      void navigate({ to: '/' })
    },
    onError: (err) => {
      toast.error(extractAuthErrorMessage(err, 'Google 登录失败，请稍后重试'))
    },
  })

  // 授权码流（popup）：onSuccess 回 { code }，发后端用 client_secret 换 token。
  const login = useGoogleLogin({
    flow: 'auth-code',
    onSuccess: ({ code }) => mutation.mutate(code),
    onError: () => toast.error('Google 登录失败，请重试'),
    onNonOAuthError: (err) => {
      // 用户主动关闭弹窗不算错误，不打扰；其余（弹窗被拦截等）给提示。
      if (err.type === 'popup_closed') return
      toast.error('Google 登录未完成，请重试')
    },
  })

  return { login: () => login(), isPending: mutation.isPending }
}
