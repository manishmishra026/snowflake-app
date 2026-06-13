import { Component, Input, OnInit, OnChanges, SimpleChanges, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ApiService, TableDataResponse } from '../../../services/api.service';

@Component({
  selector: 'app-table-viewer',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="table-viewer-card">
      <div class="card-header">
        <h3>📋 Table: {{ tableName }}</h3>
        <button class="btn btn-refresh" (click)="loadData()" [disabled]="loading">
          {{ loading ? '⏳ Refreshing...' : '🔄 Refresh' }}
        </button>
      </div>

      <div *ngIf="loading" class="spinner-container">
        <div class="loader"></div>
        <p>Fetching records from Snowflake...</p>
      </div>

      <div *ngIf="error" class="error-alert">
        <span class="lock-icon">🔒</span>
        <div class="error-details">
          <h4>Access Restricted / Query Failed</h4>
          <p>{{ error }}</p>
        </div>
      </div>

      <div *ngIf="!loading && !error && dataResponse" class="table-responsive">
        <table class="data-table" *ngIf="dataResponse.data && dataResponse.data.length > 0">
          <thead>
            <tr>
              <th *ngFor="let col of dataResponse.columns">{{ col }}</th>
            </tr>
          </thead>
          <tbody>
            <tr *ngFor="let row of dataResponse.data">
              <td *ngFor="let col of dataResponse.columns">{{ row[col] }}</td>
            </tr>
          </tbody>
        </table>
        
        <div *ngIf="!dataResponse.data || dataResponse.data.length === 0" class="no-records">
          <p>No records found in this table.</p>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .table-viewer-card {
      background: white;
      border-radius: 8px;
      box-shadow: 0 4px 12px rgba(0,0,0,0.08);
      padding: 1.5rem;
      border: 1px solid #e1e8ed;
      margin-bottom: 1.5rem;
    }
    .card-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      border-bottom: 2px solid #eaeaea;
      padding-bottom: 0.75rem;
      margin-bottom: 1.25rem;
    }
    .card-header h3 {
      margin: 0;
      color: #2c3e50;
      font-size: 1.3rem;
    }
    .btn {
      padding: 0.5rem 1rem;
      border-radius: 4px;
      font-size: 0.9rem;
      font-weight: 600;
      cursor: pointer;
      border: none;
      transition: all 0.2s;
    }
    .btn-refresh {
      background: #764ba2;
      color: white;
    }
    .btn-refresh:hover:not(:disabled) {
      background: #63398b;
      transform: translateY(-1px);
    }
    .btn:disabled {
      background: #bdc3c7;
      cursor: not-allowed;
    }
    .spinner-container {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 3rem 1.5rem;
      color: #7f8c8d;
    }
    .loader {
      border: 4px solid #f3f3f3;
      border-top: 4px solid #764ba2;
      border-radius: 50%;
      width: 30px;
      height: 30px;
      animation: spin 1s linear infinite;
      margin-bottom: 1rem;
    }
    @keyframes spin {
      0% { transform: rotate(0deg); }
      100% { transform: rotate(360deg); }
    }
    .error-alert {
      display: flex;
      gap: 1rem;
      align-items: center;
      padding: 1.5rem;
      background: #fff5f5;
      border: 1px dashed #feb2b2;
      border-radius: 6px;
      color: #c53030;
      margin-bottom: 1rem;
    }
    .lock-icon {
      font-size: 2rem;
    }
    .error-details h4 {
      margin: 0 0 0.25rem 0;
      font-size: 1.1rem;
    }
    .error-details p {
      margin: 0;
      font-size: 0.95rem;
    }
    .table-responsive {
      overflow-x: auto;
      max-height: 450px;
    }
    .data-table {
      width: 100%;
      border-collapse: collapse;
      text-align: left;
      font-size: 0.95rem;
    }
    .data-table th, .data-table td {
      padding: 0.75rem 1rem;
      border-bottom: 1px solid #e1e8ed;
    }
    .data-table th {
      background: #f5f8fa;
      color: #5f7d95;
      font-weight: 600;
      position: sticky;
      top: 0;
      z-index: 10;
    }
    .data-table tbody tr:hover {
      background: #f9f9f9;
    }
    .data-table tbody tr:nth-child(even) {
      background: #fafafa;
    }
    .no-records {
      text-align: center;
      padding: 2rem;
      color: #95a5a6;
      font-style: italic;
    }
  `]
})
export class TableViewerComponent implements OnInit, OnChanges {
  @Input() tableName!: string;
  
  loading = false;
  error: string | null = null;
  dataResponse: TableDataResponse | null = null;

  constructor(
    private apiService: ApiService,
    private cdr: ChangeDetectorRef
  ) {}

  ngOnInit(): void {
    if (this.tableName) {
      this.loadData();
    }
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['tableName'] && !changes['tableName'].firstChange) {
      this.loadData();
    }
  }

  loadData(): void {
    this.loading = true;
    this.error = null;
    this.dataResponse = null;
    this.cdr.detectChanges();

    this.apiService.getTableData(this.tableName).subscribe({
      next: (response) => {
        if (response.success) {
          this.dataResponse = response;
        } else {
          this.error = response.error;
        }
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
