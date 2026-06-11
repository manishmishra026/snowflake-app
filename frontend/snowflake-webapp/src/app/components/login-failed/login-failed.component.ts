import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';

@Component({
  selector: 'app-login-failed',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="login-failed-container">
      <div class="card">
        <div class="icon-container">
          <span class="icon">⚠️</span>
        </div>
        <h2>Authentication Failed</h2>
        <p>
          We encountered an issue while trying to authenticate your session with Azure AD.
          Please try again or contact your administrator if the problem persists.
        </p>
        <button class="btn btn-primary" (click)="retry()">
          🔄 Try Again
        </button>
      </div>
    </div>
  `,
  styles: [`
    .login-failed-container {
      display: flex;
      justify-content: center;
      align-items: center;
      min-height: 100vh;
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
      padding: 1.5rem;
    }
    .card {
      background: white;
      padding: 2.5rem;
      border-radius: 12px;
      box-shadow: 0 10px 25px rgba(0, 0, 0, 0.25);
      max-width: 450px;
      width: 100%;
      text-align: center;
    }
    .icon-container {
      margin-bottom: 1.5rem;
    }
    .icon {
      font-size: 3.5rem;
    }
    h2 {
      color: #e74c3c;
      margin-top: 0;
      margin-bottom: 1rem;
      font-size: 1.8rem;
      font-weight: 700;
    }
    p {
      color: #555;
      line-height: 1.6;
      margin-bottom: 2rem;
      font-size: 1.05rem;
    }
    .btn {
      padding: 0.85rem 2rem;
      border: none;
      border-radius: 6px;
      font-size: 1.05rem;
      cursor: pointer;
      font-weight: 600;
      transition: all 0.3s ease;
      display: inline-flex;
      align-items: center;
      gap: 0.5rem;
      background: #667eea;
      color: white;
      box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    .btn:hover {
      transform: translateY(-2px);
      box-shadow: 0 6px 15px rgba(0, 0, 0, 0.2);
      background: #5568d3;
    }
  `]
})
export class LoginFailedComponent {
  constructor(private router: Router) {}

  retry(): void {
    this.router.navigate(['/']);
  }
}
