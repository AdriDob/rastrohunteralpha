import { useState, useEffect } from 'react';

export type DeviceClass = 'mobile' | 'tablet' | 'desktop';

export interface MobileConfig {
  deviceClass: DeviceClass;
  isMobile: boolean;
  isStandalone: boolean;
  reducedData: boolean;
  reducedMotion: boolean;
  saveBattery: boolean;
  viewportWidth: number;
  viewportHeight: number;
  hasCoarsePointer: boolean;
  maxTableRows: number;
  disableCharts: boolean;
  disableAutoRefresh: boolean;
  debounceMs: number;
}

function getDeviceClass(width: number, _hasCoarse: boolean): DeviceClass {
  if (width < 768) return 'mobile';
  if (width < 1024) return 'tablet';
  return 'desktop';
}

export function detectMobileConfig(): MobileConfig {
  if (typeof window === 'undefined') {
    return {
      deviceClass: 'desktop',
      isMobile: false,
      isStandalone: false,
      reducedData: false,
      reducedMotion: false,
      saveBattery: false,
      viewportWidth: 1024,
      viewportHeight: 768,
      hasCoarsePointer: false,
      maxTableRows: 25,
      disableCharts: false,
      disableAutoRefresh: false,
      debounceMs: 300,
    };
  }

  const width = window.innerWidth;
  const height = window.innerHeight;
  const hasCoarse = matchMedia('(pointer: coarse)').matches;
  const deviceClass = getDeviceClass(width, hasCoarse);
  const isMobile = deviceClass === 'mobile';
  const isStandalone = matchMedia('(display-mode: standalone)').matches ||
    (window.navigator as any).standalone === true;

  return {
    deviceClass,
    isMobile,
    isStandalone,
    reducedData: matchMedia('(prefers-reduced-data: reduce)').matches,
    reducedMotion: matchMedia('(prefers-reduced-motion: reduce)').matches,
    saveBattery: isMobile,
    viewportWidth: width,
    viewportHeight: height,
    hasCoarsePointer: hasCoarse,
    maxTableRows: isMobile ? 10 : deviceClass === 'tablet' ? 15 : 25,
    disableCharts: isMobile,
    disableAutoRefresh: isMobile,
    debounceMs: isMobile ? 500 : 300,
  };
}

export function useMobileConfig(): MobileConfig {
  const [config] = useState(detectMobileConfig);
  return config;
}

export function useMobileConfigReactive(): MobileConfig {
  const [config, setConfig] = useState(detectMobileConfig);

  useEffect(() => {
    const handleResize = () => setConfig(detectMobileConfig());
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  return config;
}
