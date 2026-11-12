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
