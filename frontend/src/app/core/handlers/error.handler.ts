import { ErrorHandler, Injectable, Injector } from '@angular/core';
import { AppInsightsService } from '../services/app-insights.service';

@Injectable()
export class AppInsightsErrorHandler implements ErrorHandler {
  constructor(private injector: Injector) {}

  handleError(error: any): void {
    // Log to standard browser console
    console.error('Unhandled runtime error captured:', error);

    try {
      // Resolve AppInsightsService dynamically to prevent circular dependencies during bootstrap
      const appInsights = this.injector.get(AppInsightsService);
      
      const exception = error instanceof Error ? error : new Error(String(error));
      appInsights.trackException(exception, {
        url: typeof window !== 'undefined' ? window.location.href : 'unknown',
        timestamp: new Date().toISOString(),
      });
    } catch (loggingError) {
      console.error('Failed to log exception to Application Insights:', loggingError);
    }
  }
}
