import { createFileRoute, redirect } from '@tanstack/react-router';

import { LoginScreen } from '@/features/auth';
import { getSession } from '@/lib/authStore';

export const Route = createFileRoute('/login/')({
  beforeLoad: () => {
    if (getSession()) {
      throw redirect({ to: '/' });
    }
  },
  component: LoginScreen,
});
