import axios from 'axios';

export function extractAuthErrorMessage(err: unknown, fallback = '操作失败，请稍后重试'): string {
  if (axios.isAxiosError<{ message?: string }>(err)) {
    return err.response?.data?.message ?? fallback;
  }
  return fallback;
}
