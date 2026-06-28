import { Routes } from '@angular/router';
import { HomeComponent } from './components/home/home.component';
import { MsalGuard } from '@azure/msal-angular';
import { LoginFailedComponent } from './components/login-failed/login-failed.component';

export const routes: Routes = [
  { path: '', component: HomeComponent, canActivate: [MsalGuard] },
  { 
    path: 'admin', 
    loadComponent: () => import('./features/admin/admin.component').then(m => m.AdminComponent), 
    canActivate: [MsalGuard] 
  },
  { 
    path: 'reader', 
    loadComponent: () => import('./features/reader/reader.component').then(m => m.ReaderComponent), 
    canActivate: [MsalGuard] 
  },
  { 
    path: 'upload', 
    loadComponent: () => import('./features/upload/upload.component').then(m => m.UploadComponent), 
    canActivate: [MsalGuard] 
  },
  { path: 'login-failed', component: LoginFailedComponent },
  { path: '**', redirectTo: '' },
];
