import { createFileRoute } from '@tanstack/react-router';

import { OAuthCallbackScreen } from '@/features/auth';

interface CallbackSearch {
  code?: string;
  state?: string;
}

export const Route = createFileRoute('/auth/callback')({
  validateSearch: (search: Record<string, unknown>): CallbackSearch => ({
    code: typeof search.code === 'string' ? search.code : undefined,
    state: typeof search.state === 'string' ? search.state : undefined,
  }),
  component: OAuthCallbackScreen,
});
