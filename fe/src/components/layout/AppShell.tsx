import { type ReactNode } from 'react';

import Toaster from '@/components/ui/Toaster';
import TopBar from './TopBar';

const AppShell = ({ children }: { children: ReactNode }) => (
  <div className="flex h-dvh flex-col">
    <TopBar />
    <main className="mx-auto min-h-0 w-full max-w-7xl flex-1 overflow-y-auto p-3 sm:p-4">
      {children}
    </main>
    <Toaster />
  </div>
);

export default AppShell;
