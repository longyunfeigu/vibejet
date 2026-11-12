import { useMutation } from '@tanstack/react-query';
import { useNavigate } from '@tanstack/react-router';
import { toast } from 'sonner';

import { setSession } from '@/lib/authStore';

import { login } from '../api/authApi';
import { extractAuthErrorMessage } from '../helpers/authError';
import type { LoginInput } from '../types';

export function useLogin() {
  const navigate = useNavigate();
  return useMutation({
    mutationFn: (input: LoginInput) => login(input),
    onSuccess: (tokens) => {
      setSession(tokens);
      void navigate({ to: '/' });
    },
    onError: (err) => {
      toast.error(extractAuthErrorMessage(err, '登录失败，请检查网络后重试'));
    },
  });
}
