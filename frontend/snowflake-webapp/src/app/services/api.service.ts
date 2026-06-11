import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Observable, from } from 'rxjs';
import { switchMap } from 'rxjs/operators';
import { apiConfig } from '../config/auth.config';
import { AuthService } from './auth.service';

export interface TableInfo {
  schema: string;
  name: string;
}

export interface TablesResponse {
  tables: TableInfo[];
  count: number;
}

@Injectable({
  providedIn: 'root',
})
export class ApiService {
  constructor(
    private http: HttpClient,
    private authService: AuthService
  ) {}

  /**
   * Call /tables endpoint (Service Principal flow)
   * No authentication needed
   */
  listTablesByServicePrincipal(): Observable<TablesResponse> {
    const url = `${apiConfig.backendUrl}${apiConfig.endpoints.tablesServicePrincipal}`;
    return this.http.get<TablesResponse>(url);
  }

  /**
   * Call /tables-as-user endpoint (User Authentication flow with OBO)
   * Requires valid Azure AD bearer token
   */
  listTablesByUserAuth(): Observable<TablesResponse> {
    const url = `${apiConfig.backendUrl}${apiConfig.endpoints.tablesUserAuth}`;

    // Get access token and add it to the request
    return from(this.authService.getAccessToken()).pipe(
      switchMap((token) => {
        if (!token) {
          throw new Error('Unable to acquire access token');
        }

        const headers = new HttpHeaders({
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        });

        return this.http.get<TablesResponse>(url, { headers });
      })
    );
  }
}
