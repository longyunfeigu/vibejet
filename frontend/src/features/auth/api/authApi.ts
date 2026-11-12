import { apiClient } from '@/lib/apiClient';
import type { Session } from '@/lib/authStore';
import { toSession, type TokenPairResponse } from '@/lib/tokenPair';

import type { CurrentUser, LoginInput } from '../types';

interface ApiEnvelope<T> {
  code: number;
  message: string;
  data: T;
}

interface UserResponse {
  id: number;
  username: string;
  email: string;
  full_name: string | null;
  is_active: boolean;
  is_superuser: boolean;
}

export async function login(input: LoginInput): Promise<Session> {
  const res = await apiClient.post<ApiEnvelope<TokenPairResponse>>('/auth/login', input);
  return toSession(res.data.data);
}

export async function loginWithGoogle(code: string): Promise<Session> {
  const res = await apiClient.post<ApiEnvelope<TokenPairResponse>>('/auth/google', { code });
  return toSession(res.data.data);
}

export async function loginWithOAuth(provider: string, code: string): Promise<Session> {
  const res = await apiClient.post<ApiEnvelope<TokenPairResponse>>(`/auth/oauth/${provider}`, {
    code,
  });
  return toSession(res.data.data);
}

export async function fetchMe(signal?: AbortSignal): Promise<CurrentUser> {
  const res = await apiClient.get<ApiEnvelope<UserResponse>>('/auth/me', { signal });
  const u = res.data.data;
  return {
    id: u.id,
    username: u.username,
    email: u.email,
    fullName: u.full_name,
    isActive: u.is_active,
    isSuperuser: u.is_superuser,
  };
}
