import {
  ApplicationConfig,
  provideBrowserGlobalErrorListeners,
  importProvidersFrom,
  APP_INITIALIZER,
  ErrorHandler
} from '@angular/core';
import { provideRouter } from '@angular/router';
import {
  provideHttpClient,
  withInterceptorsFromDi
} from '@angular/common/http';
import { provideAnimations } from '@angular/platform-browser/animations';
import {
  MSAL_INSTANCE,
  MSAL_GUARD_CONFIG,
  MsalGuardConfiguration,
  MsalModule,
  MsalService,
  MsalGuard,
  MsalBroadcastService,
} from '@azure/msal-angular';
import { PublicClientApplication, InteractionType } from '@azure/msal-browser';
import { routes } from './app.routes';
import { ApiService } from './services/api.service';
import { AppInsightsService } from './core/services/app-insights.service';
import { AppInsightsErrorHandler } from './core/handlers/error.handler';

export function msalGuardConfigFactory(apiService: ApiService): MsalGuardConfiguration {
  const config = apiService.getCachedConfig();
  return {
    interactionType: InteractionType.Redirect,
    authRequest: {
      scopes: config?.scopes || []
    },
    loginFailedRoute: '/login-failed',
  };
}

export function msalInstanceFactory(apiService: ApiService): PublicClientApplication {
  const config = apiService.getCachedConfig();
  const clientId = config?.client_id || '00000000-0000-0000-0000-000000000000';
  const tenantId = config?.tenant_id || '00000000-0000-0000-0000-000000000000';
  return new PublicClientApplication({
    auth: {
      clientId: clientId,
      authority: `https://login.microsoftonline.com/${tenantId}`,
      redirectUri: typeof window !== 'undefined' ? window.location.origin : 'http://localhost:4200',
      postLogoutRedirectUri: typeof window !== 'undefined' ? window.location.origin : 'http://localhost:4200',
    },
    cache: {
      cacheLocation: 'localStorage',
    }
  });
}

/**
 * Bootstraps the application config, loading backend settings and
 * initializing Application Insights before the application loads.
 */
export function initializeApp(
  apiService: ApiService,
  appInsightsService: AppInsightsService
) {
  return () => {
    return new Promise<void>((resolve) => {
      apiService.getClientConfig().subscribe({
        next: (config) => {
          if (config && config.app_insights_connection_string) {
            appInsightsService.init(config.app_insights_connection_string);
          }
          resolve();
        },
        error: (err) => {
          console.error('Failed to load client config on startup:', err);
          resolve(); // Resolve to allow app to start in fallback mode
        }
      });
    });
  };
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
      deps: [ApiService]
    },
    {
      provide: MSAL_GUARD_CONFIG,
      useFactory: msalGuardConfigFactory,
      deps: [ApiService]
    },
    {
      provide: APP_INITIALIZER,
      useFactory: initializeApp,
      deps: [ApiService, AppInsightsService],
      multi: true
    },
    {
      provide: ErrorHandler,
      useClass: AppInsightsErrorHandler
    }
  ],
};
