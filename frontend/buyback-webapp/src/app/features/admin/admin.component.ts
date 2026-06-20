import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { TableViewerComponent } from '../../shared/components/table-viewer/table-viewer.component';
import { AuthService } from '../../services/auth.service';

@Component({
  selector: 'app-admin',
  standalone: true,
  imports: [CommonModule, RouterModule, TableViewerComponent],
  template: `
    <div class="admin-container">
      <header class="header">
        <div class="logo-section">
          <h1>🛡️ Buyback Admin Portal</h1>
        </div>
        <div class="nav-links">
          <a routerLink="/" class="nav-link">🏠 Home</a>
          <a routerLink="/upload" class="nav-link">📤 Upload</a>
          <span class="user-badge">👤 {{ userName }}</span>
        </div>
      </header>

      <main class="main-content">
        <div class="card selector-card">
          <h2>Admin Data Explorer</h2>
          <p>Select a table to view database records dynamically. Access is evaluated in Snowflake based on active role credentials.</p>
          <div class="table-selector">
            <button 
              *ngFor="let t of tables" 
              class="btn" 
              [class.btn-active]="selectedTable === t"
              (click)="selectTable(t)">
              {{ t }}
            </button>
          </div>
        </div>

        <app-table-viewer *ngIf="selectedTable" [tableName]="selectedTable"></app-table-viewer>
      </main>
    </div>
  `,
  styles: [`
    .admin-container {
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
      color: #e74c3c;
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
    }
    .nav-link:hover {
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
    .selector-card h2 {
      margin-top: 0;
      color: #2c3e50;
    }
    .table-selector {
      display: flex;
      gap: 1rem;
      margin-top: 1rem;
    }
    .btn {
      padding: 0.5rem 1.25rem;
      border-radius: 4px;
      font-size: 0.95rem;
      font-weight: 600;
      cursor: pointer;
      border: 1px solid #bdc3c7;
      background: white;
      color: #7f8c8d;
      transition: all 0.2s;
    }
    .btn:hover {
      background: #f8f9fa;
      border-color: #7f8c8d;
    }
    .btn-active {
      background: #e74c3c;
      color: white;
      border-color: #e74c3c;
    }
  `]
})
export class AdminComponent implements OnInit {
  userName = '';
  tables = ['EMPLOYEES', 'ADMIN_EMPLOYEES'];
  selectedTable = 'EMPLOYEES';

  constructor(private authService: AuthService) {}

  ngOnInit(): void {
    this.userName = this.authService.getUserDisplayName();
  }

  selectTable(tableName: string): void {
    this.selectedTable = tableName;
  }
}
