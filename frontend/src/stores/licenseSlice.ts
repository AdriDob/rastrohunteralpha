import type { StateCreator } from 'zustand';

export interface LicenseSlice {
  licenseValid: boolean | null;
  licenseLoading: boolean;
  licenseError: string | null;
  setLicenseValid: (v: boolean | null) => void;
  setLicenseLoading: (v: boolean) => void;
  setLicenseError: (e: string | null) => void;
}

export const createLicenseSlice: StateCreator<LicenseSlice, [], [], LicenseSlice> = (set) => ({
  licenseValid: null,
  licenseLoading: false,
  licenseError: null,
  setLicenseValid: (v) => set({ licenseValid: v }),
  setLicenseLoading: (v) => set({ licenseLoading: v }),
  setLicenseError: (e) => set({ licenseError: e }),
});
