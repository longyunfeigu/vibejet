// input: React Suspense API, @mui/material (Box, CircularProgress, Fade)
// output: SuspenseLoader 复用组件 - 项目统一 Suspense 边界 + 淡入加载占位
// owner: unknown
// pos: 通用组件 - SuspenseLoader；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
import { Suspense } from 'react';
import type { ReactNode } from 'react';
import { Box, CircularProgress, Fade } from '@mui/material';

interface SuspenseLoaderProps {
  children: ReactNode;
  fallback?: ReactNode;
}

const DefaultFallback = (): React.JSX.Element => (
  <Fade in timeout={300}>
    <Box
      sx={{
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        p: 4,
        minHeight: 120,
      }}
    >
      <CircularProgress />
    </Box>
  </Fade>
);

export const SuspenseLoader: React.FC<SuspenseLoaderProps> = ({ children, fallback }) => (
  <Suspense fallback={fallback ?? <DefaultFallback />}>{children}</Suspense>
);

export default SuspenseLoader;
