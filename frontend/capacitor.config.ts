import type { CapacitorConfig } from '@capacitor/cli';

const config: CapacitorConfig = {
  appId: 'com.vino.finanzas',
  appName: 'Fina',
  webDir: 'dist',
  server: {
    // En desarrollo, apuntar al dev server local:
    // url: 'http://192.168.x.x:5173',
    // En producción, se sirve el build estático desde dist/
    androidScheme: 'https',
    iosScheme: 'https',
  },
  plugins: {
    CapacitorHttp: {
      enabled: true,
    },
    StatusBar: {
      style: 'Dark',
      backgroundColor: '#0b0b0f',
    },
    SplashScreen: {
      launchAutoHide: true,
      backgroundColor: '#0b0b0f',
      showSpinner: false,
      androidScaleType: 'CENTER_CROP',
      splashFullScreen: true,
      splashImmersive: true,
    },
    Keyboard: {
      resize: 'body',
      resizeOnFullScreen: true,
    },
  },
};

export default config;
