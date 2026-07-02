// input: authApi.fetchMe
// output: useCurrentUser() —— 当前登录用户 suspense query
// owner: wanhua.gu
// pos: home feature - 当前用户查询 hook；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
import { useSuspenseQuery } from '@tanstack/react-query';

import { fetchMe } from '@/features/auth';

export function useCurrentUser() {
  return useSuspenseQuery({ queryKey: ['auth', 'me'], queryFn: fetchMe });
}
