// input: @react-oauth/google <GoogleLogin>, useGoogleAuth() hook
// output: GoogleSignInButton 组件 —— 渲染 Google 官方按钮，取 ID Token 后走我们后端
// owner: wanhua.gu
// pos: auth feature - Google 登录按钮(ID Token 流)；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
import { GoogleLogin } from '@react-oauth/google'
import { toast } from 'sonner'

import { useGoogleAuth } from '../hooks/useGoogleLogin'

export function GoogleSignInButton() {
  const { mutate } = useGoogleAuth()

  return (
    <GoogleLogin
      onSuccess={(resp) => {
        if (resp.credential) {
          mutate(resp.credential)
        } else {
          toast.error('未获取到 Google 凭据，请重试')
        }
      }}
      onError={() => {
        toast.error('Google 登录失败，请重试')
      }}
      text="continue_with"
      shape="pill"
    />
  )
}
