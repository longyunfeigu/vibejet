// input: 首页静态展示模块
// output: HomeMetric / HomeActivity 类型
// owner: wanhua.gu
// pos: home feature - 首页展示数据类型；一旦我被更新，务必更新我的开头注释以及所属文件夹的md

export interface HomeMetric {
  label: string;
  value: string;
  helper: string;
}

export interface HomeActivity {
  title: string;
  detail: string;
  state: 'success' | 'warning' | 'neutral';
}
