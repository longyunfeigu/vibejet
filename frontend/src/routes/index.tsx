import { createFileRoute, redirect } from '@tanstack/react-router';

import { HomeError, HomePage } from '@/features/home';
import { getSession } from '@/lib/authStore';

export const Route = createFileRoute('/')({
  beforeLoad: () => {
    if (!getSession()) {
      throw redirect({ to: '/login' });
    }
  },
  component: HomePage,
  errorComponent: HomeError,
});
