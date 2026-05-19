// input: @/lib/apiClient, ../types
// output: healthApi.getLive() - 调 backend GET /health/live
// owner: unknown
// pos: feature health - API service；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
import { apiClient } from '@/lib/apiClient';
import type { HealthLiveResponse } from '../types';

export const healthApi = {
  async getLive(): Promise<HealthLiveResponse> {
    const { data } = await apiClient.get<HealthLiveResponse>('/health/live');
    return data;
  },
};
