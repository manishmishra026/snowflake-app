import { Component, OnInit, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { ApiService } from '../../services/api.service';
import { AuthService } from '../../services/auth.service';
import { AppInsightsService } from '../../core/services/app-insights.service';

@Component({
  selector: 'app-upload',
  standalone: true,
  imports: [CommonModule, RouterModule],
  templateUrl: './upload.component.html',
  styleUrl: './upload.component.css'
})
export class UploadComponent implements OnInit {
  userName = '';
  selectedFile: File | null = null;
  loading = false;
  error: string | null = null;
  successMessage: string | null = null;
  dragOver = false;

  readonly allowedExtensions = ['.csv', '.xlsx'];
  readonly maxSizeBytes = 10 * 1024 * 1024; // 10MB

  constructor(
    private apiService: ApiService,
    private authService: AuthService,
    private appInsights: AppInsightsService,
    private cdr: ChangeDetectorRef
  ) {}

  ngOnInit(): void {
    this.userName = this.authService.getUserDisplayName();
  }

  onFileSelected(event: any): void {
    const files = event.target.files;
    if (files && files.length > 0) {
      this.handleFile(files[0]);
    }
  }

  onDragOver(event: DragEvent): void {
    event.preventDefault();
    event.stopPropagation();
    this.dragOver = true;
  }

  onDragLeave(event: DragEvent): void {
    event.preventDefault();
    event.stopPropagation();
    this.dragOver = false;
  }

  onDrop(event: DragEvent): void {
    event.preventDefault();
    event.stopPropagation();
    this.dragOver = false;

    const files = event.dataTransfer?.files;
    if (files && files.length > 0) {
      this.handleFile(files[0]);
    }
  }

  handleFile(file: File): void {
    this.error = null;
    this.successMessage = null;

    // Check extension
    const fileNameLower = file.name.toLowerCase();
    const isValidExtension = this.allowedExtensions.some(ext => fileNameLower.endsWith(ext));
    if (!isValidExtension) {
      this.error = `Invalid file type. Only ${this.allowedExtensions.join(' and ')} files are allowed.`;
      this.selectedFile = null;
      return;
    }

    // Check size
    if (file.size > this.maxSizeBytes) {
      this.error = 'File is too large. Maximum size allowed is 10MB.';
      this.selectedFile = null;
      return;
    }

    this.selectedFile = file;
    this.cdr.detectChanges();
  }

  upload(): void {
    if (!this.selectedFile) return;

    this.loading = true;
    this.error = null;
    this.successMessage = null;
    this.cdr.detectChanges();

    this.appInsights.trackEvent('FileUploadStart', { fileName: this.selectedFile.name });

    this.apiService.uploadFile(this.selectedFile).subscribe({
      next: (response) => {
        this.loading = false;
        this.successMessage = response.message || 'File uploaded successfully!';
        this.appInsights.trackEvent('FileUploadSuccess', { fileName: this.selectedFile?.name });
        this.selectedFile = null;
        this.cdr.detectChanges();
      },
      error: (err) => {
        this.loading = false;
        this.error = err.error?.detail || err.message || 'An error occurred during upload.';
        this.appInsights.trackEvent('FileUploadFailure', { 
          fileName: this.selectedFile?.name, 
          error: this.error || 'unknown' 
        });
        this.cdr.detectChanges();
      }
    });
  }

  clear(): void {
    this.selectedFile = null;
    this.error = null;
    this.successMessage = null;
    this.cdr.detectChanges();
  }
}
