import { useNavigate, useSearch } from '@tanstack/react-router';
import { Loader2 } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';

import { Button } from '@/components/ui/button';
import { setSession } from '@/lib/authStore';

import { loginWithOAuth } from '../api/authApi';
import { extractAuthErrorMessage } from '../helpers/authError';
import { takeStoredOAuthState } from '../helpers/oauthRedirect';

export function OAuthCallbackScreen() {
  const { code, state } = useSearch({ from: '/auth/callback' });
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);
  const handled = useRef(false);

  useEffect(() => {
    // StrictMode 下 effect 会跑两次；state 单次使用，用 ref 守住只处理一次。
    if (handled.current) return;
    handled.current = true;

    // 包进 async IIFE：校验失败与网络结果统一在异步流里 setState（避免 effect 体内同步 setState）。
    void (async () => {
      const stored = takeStoredOAuthState();
      if (!code || !state) {
        setError('登录回调缺少 code 或 state，请重新登录。');
        return;
      }
      if (!stored || stored !== state) {
        setError('登录状态校验失败（可能已过期或被篡改），请重新登录。');
        return;
      }

      const provider = state.split(':')[0];
      try {
        const tokens = await loginWithOAuth(provider, code);
        setSession(tokens);
        void navigate({ to: '/' });
      } catch (err) {
        setError(extractAuthErrorMessage(err, '登录失败，请重试。'));
      }
    })();
  }, [code, state, navigate]);

  return (
    <div className="flex min-h-[100dvh] items-center justify-center px-6">
      <div className="flex w-full max-w-sm flex-col items-center gap-5 text-center">
        {error ? (
          <>
            <h1 className="text-xl font-semibold tracking-tight">登录未完成</h1>
            <p className="text-muted-foreground text-sm leading-relaxed">{error}</p>
            <Button onClick={() => void navigate({ to: '/login' })} className="rounded-full">
              返回登录
            </Button>
          </>
        ) : (
          <>
            <Loader2 className="text-muted-foreground size-7 animate-spin" strokeWidth={1.5} />
            <p className="text-muted-foreground text-sm">正在完成登录…</p>
          </>
        )}
      </div>
    </div>
  );
}
