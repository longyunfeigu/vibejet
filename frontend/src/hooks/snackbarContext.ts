// input: React createContext, @mui/material AlertColor
// output: SnackbarContext + SnackbarContextValue 类型 - 供 Provider 与 hook 共享
// owner: unknown
// pos: 通用 hook 内部 - SnackbarContext；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
import { createContext } from 'react';
import type { AlertColor } from '@mui/material';

export interface SnackbarContextValue {
  show: (message: string, severity?: AlertColor) => void;
}

export const SnackbarContext = createContext<SnackbarContextValue | null>(null);
