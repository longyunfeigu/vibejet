// input: React useContext, ./snackbarContext
// output: useMuiSnackbar hook - 项目级统一通知（替代 react-toastify）
// owner: unknown
// pos: 通用 hook - useMuiSnackbar；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
import { useContext } from 'react';
import { SnackbarContext } from './snackbarContext';
import type { SnackbarContextValue } from './snackbarContext';

export const useMuiSnackbar = (): SnackbarContextValue => {
  const ctx = useContext(SnackbarContext);
  if (!ctx) {
    throw new Error('useMuiSnackbar must be used within <SnackbarProvider>');
  }
  return ctx;
};
