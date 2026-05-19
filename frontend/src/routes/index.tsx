// input: @tanstack/react-router, @mui/material
// output: 首页路由 / - 展示 Vibejet 占位 + 当前 VITE_API_URL
// owner: unknown
// pos: 路由 - 首页；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
import { createFileRoute } from '@tanstack/react-router';
import { Box, Card, CardContent, Typography } from '@mui/material';

export const Route = createFileRoute('/')({
  component: HomePage,
});

function HomePage(): React.JSX.Element {
  const apiUrl = import.meta.env.VITE_API_URL;
  return (
    <Box sx={{ display: 'flex', justifyContent: 'center', mt: { xs: 2, md: 6 } }}>
      <Card sx={{ maxWidth: 520, width: '100%' }}>
        <CardContent>
          <Typography variant="h5" gutterBottom>
            Vibejet Frontend
          </Typography>
          <Typography variant="body1" color="text.secondary" gutterBottom>
            Bootstrap scaffold is alive. Add your first feature under <code>src/features/</code> and
            route it under <code>src/routes/</code>.
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 2 }}>
            API target: <code>{apiUrl}</code>
          </Typography>
        </CardContent>
      </Card>
    </Box>
  );
}
