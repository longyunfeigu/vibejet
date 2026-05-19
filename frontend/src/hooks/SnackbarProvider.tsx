// input: ./snackbarContext, @mui/material (Snackbar, Alert)
// output: SnackbarProvider 组件 - 注入全局通知能力
// owner: unknown
// pos: 通用 hook 组件 - SnackbarProvider；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
import { useCallback, useMemo, useState } from 'react';
import type { ReactNode } from 'react';
import { Alert, Snackbar } from '@mui/material';
import type { AlertColor } from '@mui/material';
import { SnackbarContext } from './snackbarContext';
import type { SnackbarContextValue } from './snackbarContext';

interface SnackbarState {
  open: boolean;
  message: string;
  severity: AlertColor;
}

const INITIAL_STATE: SnackbarState = {
  open: false,
  message: '',
  severity: 'info',
};

export const SnackbarProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [state, setState] = useState<SnackbarState>(INITIAL_STATE);

  const show = useCallback((message: string, severity: AlertColor = 'info') => {
    setState({ open: true, message, severity });
  }, []);

  const handleClose = useCallback(() => {
    setState((prev) => ({ ...prev, open: false }));
  }, []);

  const value = useMemo<SnackbarContextValue>(() => ({ show }), [show]);

  return (
    <SnackbarContext.Provider value={value}>
      {children}
      <Snackbar
        open={state.open}
        autoHideDuration={4000}
        onClose={handleClose}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        <Alert
          onClose={handleClose}
          severity={state.severity}
          variant="filled"
          sx={{ width: '100%' }}
        >
          {state.message}
        </Alert>
      </Snackbar>
    </SnackbarContext.Provider>
  );
};

export default SnackbarProvider;
