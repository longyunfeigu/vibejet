// input: ../hooks/useHealth, @mui/material
// output: HealthCard - 展示 backend /health/live 返回状态
// owner: unknown
// pos: feature health - 组件；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
import { Card, CardContent, Chip, Stack, Typography } from '@mui/material';
import { useHealthLive } from '../hooks/useHealth';

export const HealthCard: React.FC = () => {
  const { data } = useHealthLive();
  const isAlive = data.status === 'alive';

  return (
    <Card sx={{ maxWidth: 520, width: '100%' }}>
      <CardContent>
        <Stack direction="row" spacing={2} sx={{ alignItems: 'center' }}>
          <Typography variant="h6">Backend Health</Typography>
          <Chip
            label={data.status}
            color={isAlive ? 'success' : 'warning'}
            size="small"
            variant="outlined"
          />
        </Stack>
        <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
          Source: <code>GET /health/live</code>
        </Typography>
      </CardContent>
    </Card>
  );
};

export default HealthCard;
