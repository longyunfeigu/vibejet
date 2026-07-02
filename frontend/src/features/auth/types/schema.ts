// input: zod
// output: loginSchema —— 登录表单边界校验
// owner: wanhua.gu
// pos: auth feature - 登录 schema；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
import { z } from 'zod';

export const loginSchema = z.object({
  username: z.string().min(1, '请输入用户名或邮箱'),
  password: z.string().min(1, '请输入密码'),
});

export type LoginInput = z.infer<typeof loginSchema>;
