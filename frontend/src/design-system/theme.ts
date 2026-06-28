import type { APIOptions } from 'primereact/api';

export const primeReactOptions: Partial<APIOptions> = {
  autoZIndex: true,
  cssTransition: true,
  hideOverlaysOnDocumentScrolling: false,
  locale: 'es',
  nonce: undefined,
  appendTo: 'self',
  styleContainer: undefined,
  filterMatchModeOptions: undefined,
  zIndex: {
    modal: 1100,
    overlay: 1000,
    menu: 1000,
    tooltip: 1100,
    toast: 1200,
  },
};
