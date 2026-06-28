import { Injectable } from '@angular/core';
import { ApplicationInsights } from '@microsoft/applicationinsights-web';

@Injectable({
  providedIn: 'root',
})
export class AppInsightsService {
  private appInsights?: ApplicationInsights;
  private initialized = false;

  constructor() {}

  /**
   * Initialize Application Insights client with the provided connection string.
   */
  init(connectionString: string): void {
    if (this.initialized) {
      console.warn('Application Insights is already initialized');
      return;
    }

    if (!connectionString) {
      console.log('Application Insights Connection String is empty. Telemetry export is disabled.');
      return;
    }

    try {
      this.appInsights = new ApplicationInsights({
        config: {
          connectionString: connectionString,
          enableAutoRouteTracking: true, // Automatically log page transitions
        },
      });

      this.appInsights.loadAppInsights();
      this.initialized = true;
      console.log('Application Insights initialized successfully');
    } catch (error) {
      console.error('Failed to initialize Application Insights:', error);
    }
  }

  /**
   * Log custom telemetry events.
   */
  trackEvent(name: string, properties?: { [key: string]: any }): void {
    if (this.appInsights && this.initialized) {
      this.appInsights.trackEvent({ name }, properties);
    } else {
      console.log(`[Telemetry Event]: ${name}`, properties);
    }
  }

  /**
   * Log client page views.
   */
  trackPageView(name?: string, url?: string): void {
    if (this.appInsights && this.initialized) {
      this.appInsights.trackPageView({ name, uri: url });
    } else {
      console.log(`[Telemetry PageView]: ${name || 'unknown'} (${url || ''})`);
    }
  }

  /**
   * Log unhandled exceptions.
   */
  trackException(exception: Error, properties?: { [key: string]: any }): void {
    if (this.appInsights && this.initialized) {
      this.appInsights.trackException({ exception, properties });
    } else {
      console.error('[Telemetry Exception]:', exception, properties);
    }
  }
}
