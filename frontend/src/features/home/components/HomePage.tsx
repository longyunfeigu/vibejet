import { SuspenseLoader } from '@/components/SuspenseLoader';

import { HomeDashboard } from './HomeDashboard';

function HomeSkeleton() {
  return (
    <div className="mx-auto flex min-h-[100dvh] w-full max-w-7xl flex-col gap-6 px-4 py-6 sm:px-6 lg:px-8">
      <div className="bg-muted h-16 rounded-xl" />
      <div className="bg-muted h-44 rounded-xl" />
      <div className="grid gap-4 md:grid-cols-3">
        <div className="bg-muted h-28 rounded-xl" />
        <div className="bg-muted h-28 rounded-xl" />
        <div className="bg-muted h-28 rounded-xl" />
      </div>
    </div>
  );
}

export function HomePage() {
  return (
    <SuspenseLoader fallback={<HomeSkeleton />}>
      <HomeDashboard />
    </SuspenseLoader>
  );
}
