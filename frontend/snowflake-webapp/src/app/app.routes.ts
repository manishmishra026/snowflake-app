import { Routes } from '@angular/router';
import { HomeComponent } from './components/home/home.component';
import { MsalGuard } from '@azure/msal-angular';
import { LoginFailedComponent } from './components/login-failed/login-failed.component';
import { AdminComponent } from './components/admin/admin.component';
import { ReaderComponent } from './components/reader/reader.component';

export const routes: Routes = [
  { path: '', component: HomeComponent, canActivate: [MsalGuard] },
  { path: 'admin', component: AdminComponent, canActivate: [MsalGuard] },
  { path: 'reader', component: ReaderComponent, canActivate: [MsalGuard] },
  { path: 'login-failed', component: LoginFailedComponent },
  { path: '**', redirectTo: '' },
];
