import {
  ApplicationConfig,
  provideBrowserGlobalErrorListeners,
  importProvidersFrom,
} from '@angular/core';
import { provideRouter } from '@angular/router';
import {
  provideHttpClient,
  withInterceptorsFromDi,
  HTTP_INTERCEPTORS,
} from '@angular/common/http';
import { provideAnimations } from '@angular/platform-browser/animations';
import {
  MSAL_INSTANCE,
  MSAL_GUARD_CONFIG,
  MSAL_INTERCEPTOR_CONFIG,
  MsalGuardConfiguration,
  MsalInterceptorConfiguration,
  MsalModule,
  MsalInterceptor,
  MsalService,
  MsalGuard,
  MsalBroadcastService,
} from '@azure/msal-angular';
import { PublicClientApplication, InteractionType } from '@azure/msal-browser';
import { msalConfig, loginRequest, apiConfig } from './config/auth.config';
import { routes } from './app.routes';

export function msalGuardConfigFactory(): MsalGuardConfiguration {
  return {
    interactionType: InteractionType.Redirect,
    authRequest: loginRequest,
    loginFailedRoute: '/login-failed',
  };
}

export function msalInterceptorConfigFactory(): MsalInterceptorConfiguration {
  const protectedResourceMap = new Map<string, Array<string> | null>();
  protectedResourceMap.set(
    `${apiConfig.backendUrl}${apiConfig.endpoints.tablesUserAuth}`,
    ['api://89a80661-cf8b-4e10-b3f4-b2b06be53a81/user_impersonation']
  );

  return {
    interactionType: InteractionType.Redirect,
    protectedResourceMap,
  };
}

export function msalInstanceFactory(): PublicClientApplication {
  return new PublicClientApplication(msalConfig);
}

export const appConfig: ApplicationConfig = {
  providers: [
    provideBrowserGlobalErrorListeners(),
    provideRouter(routes),
    provideHttpClient(withInterceptorsFromDi()),
    provideAnimations(),
    importProvidersFrom(MsalModule),
    MsalService,
    MsalGuard,
    MsalBroadcastService,
    {
      provide: MSAL_INSTANCE,
      useFactory: msalInstanceFactory,
    },
    {
      provide: MSAL_GUARD_CONFIG,
      useFactory: msalGuardConfigFactory,
    },
    {
      provide: MSAL_INTERCEPTOR_CONFIG,
      useFactory: msalInterceptorConfigFactory,
    },
    {
      provide: HTTP_INTERCEPTORS,
      useClass: MsalInterceptor,
      multi: true,
    },
  ],
};
