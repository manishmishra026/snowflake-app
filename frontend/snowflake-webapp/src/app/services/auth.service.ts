import { Injectable, OnDestroy } from '@angular/core';
import { MsalService, MsalBroadcastService } from '@azure/msal-angular';
import { AccountInfo, AuthenticationResult, EventMessage, EventType } from '@azure/msal-browser';
import { BehaviorSubject, Subject } from 'rxjs';
import { filter, takeUntil } from 'rxjs/operators';
import { firstValueFrom } from 'rxjs';
import { loginRequest } from '../config/auth.config';

@Injectable({
  providedIn: 'root',
})
export class AuthService implements OnDestroy {
  private isLoggedIn$ = new BehaviorSubject<boolean>(false);
  private userProfile$ = new BehaviorSubject<AccountInfo | null>(null);

  private destroy$ = new Subject<void>();

  constructor(
    private msalService: MsalService,
    private msalBroadcast: MsalBroadcastService
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
              return;
            }
            const authResult = result.payload as AuthenticationResult;
            if (authResult) {
              this.isLoggedIn$.next(true);
              const accounts = this.msalService.instance.getAllAccounts();
              if (accounts.length > 0) {
                this.userProfile$.next(accounts[0]);
              }
            }
          });
      },
      error: (error) => {
        console.error('MSAL initialization failed:', error);
      },
    });
  }

  login(): void {
    this.msalService.loginRedirect(loginRequest);
  }

  logout(): void {
    this.msalService.logoutRedirect();
  }

  async getAccessToken(): Promise<string | null> {
    const accounts = this.msalService.instance.getAllAccounts();
    if (accounts.length === 0) return null;

    try {
      const result = await firstValueFrom(
        this.msalService.acquireTokenSilent({
          scopes: loginRequest.scopes,
          account: accounts[0],
        })
      );
      return result?.accessToken || null;
    } catch (error) {
      console.error('Failed to acquire token:', error);
      return null;
    }
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
}
