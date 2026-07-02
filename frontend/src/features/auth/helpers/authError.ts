// input: 未知错误对象（可能是 AxiosError）
// output: extractAuthErrorMessage() —— 从错误中提取后端 message 或回退文案
// owner: wanhua.gu
// pos: auth feature - 认证错误信息提取(useLogin/useGoogleAuth 共用)；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
import axios from 'axios'

export function extractAuthErrorMessage(
  err: unknown,
  fallback = '操作失败，请稍后重试',
): string {
  if (axios.isAxiosError<{ message?: string }>(err)) {
    return err.response?.data?.message ?? fallback
  }
  return fallback
}
