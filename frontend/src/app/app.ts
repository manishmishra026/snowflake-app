import { Component, OnInit } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { MsalModule, MsalService } from '@azure/msal-angular';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet, MsalModule],
  templateUrl: './app.html',
  styleUrl: './app.css'
})
export class App implements OnInit {
  constructor(private msalService: MsalService) {}

  ngOnInit(): void {
    // Initialize MSAL and handle redirect callbacks
    this.msalService.initialize().subscribe(() => {
      this.msalService.handleRedirectObservable().subscribe({
        next: (result) => {
          if (result) {
            this.msalService.instance.setActiveAccount(result.account);
          }
        },
        error: (error) => {
          console.error('Redirect authentication handling failed:', error);
        }
      });
    });
  }
}
