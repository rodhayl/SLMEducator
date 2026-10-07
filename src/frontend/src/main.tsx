import { flushSync } from 'react-dom';
import { createRoot } from 'react-dom/client';
import { QueryClientProvider } from '@tanstack/react-query';
import { RouterProvider } from 'react-router';
import '@/i18n';
import '@/styles/tokens.css';
import '@/styles/base.css';
import { AppearanceProvider } from '@/app/AppearanceProvider';
import { AuthProvider } from '@/app/AuthProvider';
import { createQueryClient } from '@/lib/query';
import { requestLegacyWorkerUpdate } from '@/app/retire-legacy-worker';
import { router } from '@/app/router';
const queries = createQueryClient();
createRoot(document.getElementById('root')!).render(<QueryClientProvider client={queries}><AppearanceProvider><AuthProvider><RouterProvider router={router} flushSync={fn => { flushSync(fn); return undefined; }}/></AuthProvider></AppearanceProvider></QueryClientProvider>);

void requestLegacyWorkerUpdate();
