import { Component, OnInit, OnDestroy, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Subject } from 'rxjs';
import { takeUntil } from 'rxjs/operators';
import { AuthService } from '../../services/auth.service';
import { ApiService, TablesResponse } from '../../services/api.service';

type FlowType = 'service-principal' | 'user-auth' | null;

@Component({
  selector: 'app-home',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './home.component.html',
  styleUrl: './home.component.css',
})
export class HomeComponent implements OnInit, OnDestroy {
  isLoggedIn = false;
  userName = '';
  loading = false;
  error: string | null = null;
  tablesData: TablesResponse | null = null;
  currentFlow: FlowType = null;

  private destroy$ = new Subject<void>();

  constructor(
    private authService: AuthService,
    private apiService: ApiService,
    private cdr: ChangeDetectorRef
  ) {}

  ngOnInit(): void {
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
    this.currentFlow = null;
    this.error = null;
  }

  /**
   * Fetch tables using Service Principal flow (no auth required)
   */
  fetchTablesByServicePrincipal(): void {
    this.loading = true;
    this.error = null;
    this.currentFlow = 'service-principal';
    this.tablesData = null;

    this.apiService.listTablesByServicePrincipal().subscribe({
      next: (response) => {
        this.tablesData = response;
        this.loading = false;
        this.cdr.detectChanges();
      },
      error: (err) => {
        console.error('Error fetching tables (service principal):', err);
        this.error = err.message || 'Failed to fetch tables';
        this.loading = false;
        this.currentFlow = null;
        this.cdr.detectChanges();
      },
    });
  }

  /**
   * Fetch tables using User Authentication flow (Azure AD OBO)
   */
  fetchTablesByUserAuth(): void {
    if (!this.isLoggedIn) {
      this.error = 'Please login first to use user authentication flow';
      return;
    }

    this.loading = true;
    this.error = null;
    this.currentFlow = 'user-auth';
    this.tablesData = null;

    this.apiService.listTablesByUserAuth().subscribe({
      next: (response) => {
        this.tablesData = response;
        this.loading = false;
        this.cdr.detectChanges();
      },
      error: (err) => {
        console.error('Error fetching tables (user auth):', err);
        this.error = err.message || 'Failed to fetch tables';
        this.loading = false;
        this.currentFlow = null;
        this.cdr.detectChanges();
      },
    });
  }

  getFlowName(): string {
    if (this.currentFlow === 'service-principal') return 'Service Principal';
    if (this.currentFlow === 'user-auth') return 'User Authentication (OBO)';
    return '';
  }
}
