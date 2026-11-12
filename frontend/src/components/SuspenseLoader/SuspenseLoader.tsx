import { Suspense, type ReactNode } from 'react';

import { Skeleton } from '@/components/ui/skeleton';

interface SuspenseLoaderProps {
  children: ReactNode;
  fallback?: ReactNode;
}

function DefaultFallback() {
  return (
    <div className="flex w-full max-w-sm flex-col gap-3">
      <Skeleton className="h-8 w-1/2" />
      <Skeleton className="h-4 w-3/4" />
      <Skeleton className="h-4 w-2/3" />
    </div>
  );
}

export function SuspenseLoader({ children, fallback }: SuspenseLoaderProps) {
  return <Suspense fallback={fallback ?? <DefaultFallback />}>{children}</Suspense>;
}
