// input: @tanstack/react-router, ~components/layout (AppLayout)
// output: TanStack Router 根路由 - 所有页面套用 AppLayout
// owner: unknown
// pos: 路由 - 根路由；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
import { Outlet, createRootRoute } from '@tanstack/react-router';
import { AppLayout } from '~components/layout';

export const Route = createRootRoute({
  component: RootComponent,
});

function RootComponent(): React.JSX.Element {
  return (
    <AppLayout>
      <Outlet />
    </AppLayout>
  );
}
