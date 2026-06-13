import { Component, OnInit, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { ApiService, TableDataResponse } from '../../services/api.service';
import { AuthService } from '../../services/auth.service';

@Component({
  selector: 'app-admin',
  standalone: true,
  imports: [CommonModule, RouterModule],
  template: `
    <div class="container">
      <header class="header">
        <div class="logo-section">
          <h1>🛡️ Snowflake Admin Portal</h1>
        </div>
        <div class="nav-links">
          <a routerLink="/" class="nav-link">🏠 Home</a>
          <span class="user-badge">👤 {{ userName }}</span>
        </div>
      </header>

      <main class="main-content">
        <div class="card action-card">
          <h2>Database Queries</h2>
          <p>This page tests queries on both <code>EMPLOYEES</code> and <code>ADMIN_EMPLOYEES</code>. Snowflake will dynamically resolve access permissions based on your active role.</p>
          <div class="actions-group">
            <button class="btn btn-primary" (click)="fetchTableData()" [disabled]="loading">
              {{ loading ? '⏳ Fetching Data...' : '📊 Get Table Data' }}
            </button>
          </div>
        </div>

        <!-- Error Alert -->
        <div *ngIf="error" class="alert alert-danger">
          <strong>Error:</strong> {{ error }}
        </div>

        <!-- Results Grid -->
        <div *ngIf="dataResults" class="results-grid">
          <!-- Employees Table Section -->
          <div class="card data-card">
            <h3>📋 Table: EMPLOYEES</h3>
            <ng-container *ngIf="dataResults.employees.success; else noEmployeesAccess">
              <div class="table-responsive">
                <table class="data-table">
                  <thead>
                    <tr>
                      <th>ID</th>
                      <th>First Name</th>
                      <th>Last Name</th>
                      <th>Department</th>
                      <th>Job Title</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr *ngFor="let row of dataResults.employees.data">
                      <td>{{ row.EMPLOYEE_ID }}</td>
                      <td>{{ row.FIRST_NAME }}</td>
                      <td>{{ row.LAST_NAME }}</td>
                      <td>{{ row.DEPARTMENT }}</td>
                      <td>{{ row.JOB_TITLE }}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </ng-container>
            <ng-template #noEmployeesAccess>
              <div class="access-denied-box">
                <span class="lock-icon">🔒</span>
                <p class="denied-message">{{ dataResults.employees.error }}</p>
              </div>
            </ng-template>
          </div>

          <!-- Admin Employees Table Section -->
          <div class="card data-card">
            <h3>👑 Table: ADMIN_EMPLOYEES</h3>
            <ng-container *ngIf="dataResults.admin_employees.success; else noAdminAccess">
              <div class="table-responsive">
                <table class="data-table">
                  <thead>
                    <tr>
                      <th>ID</th>
                      <th>First Name</th>
                      <th>Last Name</th>
                      <th>Department</th>
                      <th>Job Title</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr *ngFor="let row of dataResults.admin_employees.data">
                      <td>{{ row.EMPLOYEE_ID }}</td>
                      <td>{{ row.FIRST_NAME }}</td>
                      <td>{{ row.LAST_NAME }}</td>
                      <td>{{ row.DEPARTMENT }}</td>
                      <td>{{ row.JOB_TITLE }}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </ng-container>
            <ng-template #noAdminAccess>
              <div class="access-denied-box">
                <span class="lock-icon">🔒</span>
                <p class="denied-message">{{ dataResults.admin_employees.error }}</p>
              </div>
            </ng-template>
          </div>
        </div>
      </main>
    </div>
  `,
  styles: [`
    .container {
      max-width: 1200px;
      margin: 0 auto;
      padding: 1.5rem;
      font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
    }
    .header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding-bottom: 1.5rem;
      border-bottom: 2px solid #eaeaea;
      margin-bottom: 2rem;
    }
    .header h1 {
      margin: 0;
      font-size: 1.8rem;
      color: #2c3e50;
    }
    .nav-links {
      display: flex;
      align-items: center;
      gap: 1.25rem;
    }
    .nav-link {
      color: #3498db;
      text-decoration: none;
      font-weight: 500;
      transition: color 0.2s;
    }
    .nav-link:hover {
      color: #2980b9;
      text-decoration: underline;
    }
    .user-badge {
      background: #ecf0f1;
      padding: 0.4rem 0.8rem;
      border-radius: 20px;
      font-size: 0.9rem;
      color: #34495e;
      font-weight: 500;
    }
    .card {
      background: white;
      border-radius: 8px;
      box-shadow: 0 4px 12px rgba(0,0,0,0.08);
      padding: 1.5rem;
      margin-bottom: 1.5rem;
      border: 1px solid #e1e8ed;
    }
    .action-card h2 {
      margin-top: 0;
      color: #2c3e50;
    }
    .btn {
      padding: 0.75rem 1.5rem;
      border-radius: 6px;
      font-size: 1rem;
      font-weight: 600;
      cursor: pointer;
      border: none;
      transition: background 0.2s, transform 0.1s;
    }
    .btn-primary {
      background: #e74c3c; /* Reddish shade for Admin Portal */
      color: white;
    }
    .btn-primary:hover:not(:disabled) {
      background: #c0392b;
      transform: translateY(-1px);
    }
    .btn:disabled {
      background: #bdc3c7;
      cursor: not-allowed;
    }
    .alert {
      padding: 1rem;
      border-radius: 6px;
      margin-bottom: 1.5rem;
    }
    .alert-danger {
      background: #fde8e8;
      border: 1px solid #f8b4b4;
      color: #9b1c1c;
    }
    .results-grid {
      display: grid;
      grid-template-columns: 1fr;
      gap: 1.5rem;
    }
    @media (min-width: 900px) {
      .results-grid {
        grid-template-columns: 1fr 1fr;
      }
    }
    .data-card h3 {
      margin-top: 0;
      border-bottom: 2px solid #eaeaea;
      padding-bottom: 0.5rem;
      color: #2c3e50;
    }
    .table-responsive {
      overflow-x: auto;
      max-height: 400px;
    }
    .data-table {
      width: 100%;
      border-collapse: collapse;
      text-align: left;
    }
    .data-table th, .data-table td {
      padding: 0.75rem;
      border-bottom: 1px solid #e1e8ed;
    }
    .data-table th {
      background: #f5f8fa;
      color: #5f7d95;
      font-weight: 600;
    }
    .access-denied-box {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 3rem 1.5rem;
      background: #fff5f5;
      border: 2px dashed #feb2b2;
      border-radius: 8px;
      color: #c53030;
    }
    .lock-icon {
      font-size: 2.5rem;
      margin-bottom: 1rem;
    }
    .denied-message {
      font-size: 1.1rem;
      font-weight: 600;
      margin: 0;
      text-align: center;
    }
  `]
})
export class AdminComponent implements OnInit {
  userName = '';
  loading = false;
  error: string | null = null;
  dataResults: TableDataResponse | null = null;

  constructor(
    private apiService: ApiService,
    private authService: AuthService,
    private cdr: ChangeDetectorRef
  ) {}

  ngOnInit(): void {
    this.userName = this.authService.getUserDisplayName();
  }

  fetchTableData(): void {
    this.loading = true;
    this.error = null;
    this.dataResults = null;
    this.cdr.detectChanges();

    this.apiService.listTableDataByUserAuth().subscribe({
      next: (response) => {
        this.dataResults = response;
        this.loading = false;
        this.cdr.detectChanges();
      },
      error: (err) => {
        console.error('Error fetching table data:', err);
        this.error = err.message || 'Failed to fetch table data';
        this.loading = false;
        this.cdr.detectChanges();
      }
    });
  }
}
