// input: backend /health/live response shape
// output: HealthLiveResponse type
// owner: unknown
// pos: feature health - 类型；一旦我被更新，务必更新我的开头注释以及所属文件夹的md

export interface HealthLiveResponse {
  status: 'alive' | string;
}
