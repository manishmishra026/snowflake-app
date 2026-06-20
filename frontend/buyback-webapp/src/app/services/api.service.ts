import { Injectable, Injector } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Observable, from, of } from 'rxjs';
import { switchMap, tap } from 'rxjs/operators';
import { AuthService } from './auth.service';

export interface TableInfo {
  schema: string;
  name: string;
}

export interface TablesResponse {
  tables: TableInfo[];
  count: number;
}

export interface ClientConfigResponse {
  app_insights_connection_string: string;
  client_id: string;
  tenant_id: string;
  scopes: string[];
  backend_url: string;
}

export interface TableDataResponse {
  success: boolean;
  table_name: string;
  data: any[] | null;
  columns: string[] | null;
  error: string | null;
}

@Injectable({
  providedIn: 'root',
})
export class ApiService {
  private clientConfig: ClientConfigResponse | null = null;

  private authService?: AuthService;

  constructor(
    private http: HttpClient,
    private injector: Injector
  ) {}

  private getAuthService(): AuthService {
    if (!this.authService) {
      this.authService = this.injector.get(AuthService);
    }
    return this.authService;
  }

  getCachedConfig(): ClientConfigResponse | null {
    return this.clientConfig;
  }

  /**
   * Fetch dynamic configurations from backend.
   */
  getClientConfig(): Observable<ClientConfigResponse> {
    if (this.clientConfig) {
      return of(this.clientConfig);
    }
    const url = '/assets/config/config.json';
    return this.http.get<ClientConfigResponse>(url).pipe(
      tap((config) => {
        this.clientConfig = config;
      })
    );
  }

  /**
   * Internal helper to attach auth headers if user is authenticated.
   */
  private getRequestOptions(): Observable<{ headers: HttpHeaders }> {
    const authService = this.getAuthService();
    return from(authService.getAccessToken()).pipe(
      switchMap((token) => {
        if (!token) {
          throw new Error('Unable to acquire Azure AD authentication token. Please try logging out and logging in again to refresh your session.');
        }
        const headers = new HttpHeaders({
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        });
        return of({ headers });
      })
    );
  }

  getBackendUrl(): string {
    return this.clientConfig?.backend_url || 'http://localhost:8000';
  }

  /**
   * Fetch all tables dynamically.
   */
  listTables(): Observable<TablesResponse> {
    return this.getRequestOptions().pipe(
      switchMap((options) => {
        const url = `${this.getBackendUrl()}/tables`;
        return this.http.get<TablesResponse>(url, options);
      })
    );
  }

  /**
   * Fetch table data dynamically.
   */
  getTableData(tableName: string, limit: number = 50): Observable<TableDataResponse> {
    return this.getRequestOptions().pipe(
      switchMap((options) => {
        const url = `${this.getBackendUrl()}/tables/${tableName}/data?limit=${limit}`;
        return this.http.get<TableDataResponse>(url, options);
      })
    );
  }
}
