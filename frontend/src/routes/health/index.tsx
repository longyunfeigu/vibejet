// input: @tanstack/react-router, ~components/SuspenseLoader, ~features (lazy)
// output: /health 路由 - lazy 加载 HealthCard，外层包 SuspenseLoader
// owner: unknown
// pos: 路由 - /health；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
import { lazy } from 'react';
import { createFileRoute } from '@tanstack/react-router';
import { Box } from '@mui/material';
import { SuspenseLoader } from '~components/SuspenseLoader';

const HealthCard = lazy(() => import('~features/health').then((m) => ({ default: m.HealthCard })));

export const Route = createFileRoute('/health/')({
  component: HealthPage,
});

function HealthPage(): React.JSX.Element {
  return (
    <Box sx={{ display: 'flex', justifyContent: 'center', mt: { xs: 2, md: 6 } }}>
      <SuspenseLoader>
        <HealthCard />
      </SuspenseLoader>
    </Box>
  );
}
