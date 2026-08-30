import { type ReactNode } from 'react';

import Toaster from '@/components/ui/Toaster';
import TopBar from './TopBar';

const AppShell = ({ children }: { children: ReactNode }) => (
  <div className="flex min-h-full flex-col">
    <TopBar />
    <main className="mx-auto w-full max-w-7xl flex-1 p-4 sm:p-6">{children}</main>
    <Toaster />
  </div>
);

export default AppShell;
