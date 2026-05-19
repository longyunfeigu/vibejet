// input: @testing-library/react, ./SuspenseLoader
// output: SuspenseLoader 单元测试 - 验证 children 渲染与 fallback 行为
// owner: unknown
// pos: 通用组件 SuspenseLoader 的测试；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
import { render, screen } from '@testing-library/react';
import { lazy } from 'react';
import { describe, it, expect } from 'vitest';
import { SuspenseLoader } from './SuspenseLoader';

describe('SuspenseLoader', () => {
  it('renders children when not suspended', () => {
    render(
      <SuspenseLoader>
        <span>hello</span>
      </SuspenseLoader>,
    );
    expect(screen.getByText('hello')).toBeInTheDocument();
  });

  it('renders default fallback while children suspend', () => {
    const NeverResolve = lazy(() => new Promise(() => {}) as Promise<{ default: React.FC }>);
    render(
      <SuspenseLoader>
        <NeverResolve />
      </SuspenseLoader>,
    );
    expect(screen.getByRole('progressbar')).toBeInTheDocument();
  });

  it('renders custom fallback when provided', () => {
    const NeverResolve = lazy(() => new Promise(() => {}) as Promise<{ default: React.FC }>);
    render(
      <SuspenseLoader fallback={<span>loading…</span>}>
        <NeverResolve />
      </SuspenseLoader>,
    );
    expect(screen.getByText('loading…')).toBeInTheDocument();
  });
});
