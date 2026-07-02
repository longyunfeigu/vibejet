// input: authApi.login, authStore.setSession, router navigate, sonner toast
// output: useLogin() —— 登录 mutation(成功存会话+跳转, 失败 toast)
// owner: wanhua.gu
// pos: auth feature - 登录用例编排 hook；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
import { useMutation } from '@tanstack/react-query'
import { useNavigate } from '@tanstack/react-router'
import { toast } from 'sonner'

import { setSession } from '@/lib/authStore'

import { login } from '../api/authApi'
import { extractAuthErrorMessage } from '../helpers/authError'
import type { LoginInput } from '../types'

export function useLogin() {
  const navigate = useNavigate()
  return useMutation({
    mutationFn: (input: LoginInput) => login(input),
    onSuccess: (tokens) => {
      setSession({ accessToken: tokens.accessToken, refreshToken: tokens.refreshToken })
      void navigate({ to: '/' })
    },
    onError: (err) => {
      toast.error(extractAuthErrorMessage(err, '登录失败，请检查网络后重试'))
    },
  })
}
