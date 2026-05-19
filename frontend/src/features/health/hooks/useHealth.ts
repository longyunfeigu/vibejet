// input: @tanstack/react-query (useSuspenseQuery), ../api/healthApi
// output: useHealthLive Suspense hook - 配合外层 SuspenseLoader 使用
// owner: unknown
// pos: feature health - hook；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
import { useSuspenseQuery } from '@tanstack/react-query';
import { healthApi } from '../api/healthApi';

export const useHealthLive = () =>
  useSuspenseQuery({
    queryKey: ['health', 'live'],
    queryFn: () => healthApi.getLive(),
    staleTime: 10_000,
  });
