import { Component, OnInit, OnDestroy, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Subject } from 'rxjs';
import { takeUntil } from 'rxjs/operators';
import { RouterModule } from '@angular/router';
import { AuthService } from '../../services/auth.service';
import { ApiService, TablesResponse, ClientConfigResponse } from '../../services/api.service';
import { TableViewerComponent } from '../../shared/components/table-viewer/table-viewer.component';
import { AppInsightsService } from '../../core/services/app-insights.service';

@Component({
  selector: 'app-home',
  standalone: true,
  imports: [CommonModule, RouterModule, TableViewerComponent],
  templateUrl: './home.component.html',
  styleUrl: './home.component.css',
})
export class HomeComponent implements OnInit, OnDestroy {
  isLoggedIn = false;
  userName = '';
  loading = false;
  error: string | null = null;
  tablesData: TablesResponse | null = null;
  selectedTable: string | null = null;
  clientConfig: ClientConfigResponse | null = null;

  private destroy$ = new Subject<void>();

  constructor(
    private authService: AuthService,
    private apiService: ApiService,
    private appInsights: AppInsightsService,
    private cdr: ChangeDetectorRef
  ) {}

  ngOnInit(): void {
    // 1. Fetch dynamic settings from API
    this.apiService.getClientConfig()
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (config) => {
          this.clientConfig = config;
          this.cdr.detectChanges();
        },
        error: (err) => {
          console.error('Failed to retrieve client configuration settings:', err);
          this.error = 'Unable to establish server config connections.';
          this.cdr.detectChanges();
        }
      });

    // 2. Track authentication state
    this.authService
      .isLoggedIn()
      .pipe(takeUntil(this.destroy$))
      .subscribe((loggedIn) => {
        this.isLoggedIn = loggedIn;
        this.cdr.detectChanges();
      });

    this.authService
      .getUserProfile()
      .pipe(takeUntil(this.destroy$))
      .subscribe((profile) => {
        if (profile) {
          this.userName = this.authService.getUserDisplayName();
          this.cdr.detectChanges();
        }
      });
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  login(): void {
    this.authService.login();
  }

  logout(): void {
    this.authService.logout();
    this.tablesData = null;
    this.selectedTable = null;
    this.error = null;
  }

  /**
   * Query database tables using abstract backend authentication
   */
  fetchTables(): void {
    if (!this.isLoggedIn) {
      this.error = 'Login with Azure AD is required to fetch tables.';
      return;
    }

    this.loading = true;
    this.error = null;
    this.tablesData = null;
    this.selectedTable = null;
    this.cdr.detectChanges();

    this.appInsights.trackEvent('FetchTablesStart');

    this.apiService.listTables().subscribe({
      next: (response) => {
        this.tablesData = response;
        this.loading = false;
        this.appInsights.trackEvent('FetchTablesSuccess', { count: response.count });
        this.cdr.detectChanges();
      },
      error: (err) => {
        console.error('Error fetching tables from server:', err);
        this.error = err.message || 'Failed to list database tables';
        this.loading = false;
        this.appInsights.trackEvent('FetchTablesFailure', { error: err.message || 'unknown' });
        this.cdr.detectChanges();
      },
    });
  }

  /**
   * Set target table to view rows and schemas
   */
  viewTableData(tableName: string): void {
    this.selectedTable = tableName;
    this.appInsights.trackEvent('ViewTableData', { tableName });
    this.cdr.detectChanges();
  }

  hasRole(role: string): boolean {
    return this.authService.hasRole(role);
  }
}
