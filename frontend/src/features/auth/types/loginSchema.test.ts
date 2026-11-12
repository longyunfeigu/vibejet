import { describe, expect, it } from 'vitest';

import { loginSchema } from './index';

describe('loginSchema', () => {
  it('拒绝空的用户名或密码', () => {
    expect(loginSchema.safeParse({ username: '', password: '' }).success).toBe(false);
    expect(loginSchema.safeParse({ username: 'alice', password: '' }).success).toBe(false);
  });

  it('接受非空用户名 + 密码', () => {
    expect(loginSchema.safeParse({ username: 'alice', password: 'secret12' }).success).toBe(true);
  });
});
