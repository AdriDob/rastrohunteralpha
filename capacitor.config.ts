import { defineConfig } from '@capacitor/cli';

export default defineConfig({
  appId: 'ai.rastro.app',
  appName: 'Rastro',
  webDir: 'frontend/dist',
  server: {
    androidScheme: 'https',
    cleartext: false,
  },
  android: {
    backgroundColor: '#0d0f17',
    buildOptions: {
      keystorePath: undefined,
      keystoreAlias: undefined,
    },
  },
  plugins: {
    PushNotifications: {
      presentationOptions: ['badge', 'sound', 'alert'],
    },
    SplashScreen: {
      backgroundColor: '#0d0f17',
      showSpinner: false,
    },
  },
});
