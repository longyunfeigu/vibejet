// input: @mui/material (AppBar, Toolbar, Typography, Box), children
// output: AppLayout 组件 - 顶部 AppBar + 主内容容器
// owner: unknown
// pos: layout 组件 - AppLayout；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
import { AppBar, Box, Toolbar, Typography } from '@mui/material';
import type { ReactNode } from 'react';

interface AppLayoutProps {
  children: ReactNode;
}

export const AppLayout: React.FC<AppLayoutProps> = ({ children }) => (
  <Box sx={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
    <AppBar position="static" elevation={0}>
      <Toolbar>
        <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
          Vibejet
        </Typography>
      </Toolbar>
    </AppBar>
    <Box component="main" sx={{ flexGrow: 1, p: { xs: 2, md: 4 } }}>
      {children}
    </Box>
  </Box>
);

export default AppLayout;
