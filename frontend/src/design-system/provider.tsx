import type { ReactNode } from 'react';
import { PrimeReactProvider } from 'primereact/api';
import { primeReactOptions } from './theme';

export function RastroDesignSystemProvider({ children }: { children: ReactNode }) {
  return (
    <PrimeReactProvider value={primeReactOptions}>
      {children}
    </PrimeReactProvider>
  );
}
