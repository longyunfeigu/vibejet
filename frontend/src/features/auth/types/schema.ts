import { z } from 'zod';

export const loginSchema = z.object({
  username: z.string().min(1, '请输入用户名或邮箱'),
  password: z.string().min(1, '请输入密码'),
});

export type LoginInput = z.infer<typeof loginSchema>;
