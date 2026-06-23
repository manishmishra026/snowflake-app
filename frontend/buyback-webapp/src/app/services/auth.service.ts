import { Inject, Injectable, OnDestroy } from '@angular/core';
import { MsalService, MsalBroadcastService, MSAL_GUARD_CONFIG, MsalGuardConfiguration } from '@azure/msal-angular';
import { AccountInfo, AuthenticationResult, EventMessage, EventType } from '@azure/msal-browser';
import { BehaviorSubject, Subject } from 'rxjs';
import { filter, takeUntil } from 'rxjs/operators';
import { firstValueFrom } from 'rxjs';
import { AppInsightsService } from '../core/services/app-insights.service';

@Injectable({
  providedIn: 'root',
})
export class AuthService implements OnDestroy {
  private isLoggedIn$ = new BehaviorSubject<boolean>(false);
  private userProfile$ = new BehaviorSubject<AccountInfo | null>(null);

  private destroy$ = new Subject<void>();

  constructor(
    private msalService: MsalService,
    private msalBroadcast: MsalBroadcastService,
    private appInsights: AppInsightsService,
    @Inject(MSAL_GUARD_CONFIG) private msalGuardConfig: MsalGuardConfiguration
  ) {
    this.initializeAuth();
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  private initializeAuth(): void {
    this.msalService.initialize().subscribe({
      next: () => {
        const accounts = this.msalService.instance.getAllAccounts();
        if (accounts.length > 0) {
          this.isLoggedIn$.next(true);
          this.userProfile$.next(accounts[0]);
        }

        this.msalBroadcast.msalSubject$
          .pipe(
            filter(
              (msg: EventMessage) =>
                msg.eventType === EventType.LOGIN_SUCCESS ||
                msg.eventType === EventType.ACQUIRE_TOKEN_SUCCESS ||
                msg.eventType === EventType.LOGOUT_SUCCESS
            ),
            takeUntil(this.destroy$)
          )
          .subscribe((result: EventMessage) => {
            if (result.eventType === EventType.LOGOUT_SUCCESS) {
              this.isLoggedIn$.next(false);
              this.userProfile$.next(null);
              this.appInsights.trackEvent('UserLogout');
              return;
            }
            const authResult = result.payload as AuthenticationResult;
            if (authResult) {
              this.isLoggedIn$.next(true);
              const accounts = this.msalService.instance.getAllAccounts();
              if (accounts.length > 0) {
                this.userProfile$.next(accounts[0]);
                this.appInsights.trackEvent('UserLogin', {
                  username: accounts[0].username,
                  name: accounts[0].name
                });
              }
            }
          });
      },
      error: (error) => {
        console.error('MSAL initialization failed:', error);
      },
    });
  }

  private getGuardAuthRequest(): any {
    const authReq = this.msalGuardConfig.authRequest;
    if (typeof authReq === 'function') {
      return authReq(this.msalService, {} as any);
    }
    return authReq;
  }

  login(): void {
    const req = this.getGuardAuthRequest();
    this.msalService.loginRedirect(req);
  }

  logout(): void {
    this.msalService.logoutRedirect();
  }

  async getAccessToken(): Promise<string | null> {
    const accounts = this.msalService.instance.getAllAccounts();
    if (accounts.length === 0) return null;
    return accounts[0].idToken || null;
  }

  isLoggedIn() {
    return this.isLoggedIn$.asObservable();
  }

  getUserProfile() {
    return this.userProfile$.asObservable();
  }

  getUserDisplayName(): string {
    const profile = this.userProfile$.value;
    return profile?.name || profile?.username || 'User';
  }

  getUserRoles(): string[] {
    const profile = this.userProfile$.value;
    if (profile) {
      console.log('User Profile ID Token Claims:', profile.idTokenClaims);
    }
    if (profile && profile.idTokenClaims && (profile.idTokenClaims as any).roles) {
      const rawRoles = (profile.idTokenClaims as any).roles as string[];
      return rawRoles.map(role => {
        const lowerRole = role.toLowerCase().trim();
        if (lowerRole === 'ceb213da-f557-4a7b-94d7-3e0a1cea2b22' || lowerRole === 'admin' || lowerRole === 'admins') {
          return 'admins';
        }
        if (lowerRole === 'reader' || lowerRole === 'readers') {
          return 'readers';
        }
        return role;
      });
    }
    return [];
  }

  hasRole(role: string): boolean {
    return this.getUserRoles().includes(role);
  }
}
