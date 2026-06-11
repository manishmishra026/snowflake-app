import { Configuration, LogLevel } from '@azure/msal-browser';

/**
 * Authentication Configuration
 * 
 * IMPORTANT: Update the following values in this file:
 * - clientId: Your Azure AD Application (Client) ID
 * - tenantId: Your Azure AD Tenant ID
 * 
 * You can find these values in:
 * 1. Azure Portal → App registrations → Your app
 * 2. Overview page shows Application (client) ID and Directory (tenant) ID
 */

export const msalConfig: Configuration = {
  auth: {
    clientId: '183b3bcc-4183-4566-a467-7d2f945c5880', // Replace with your Application (Client) ID
    authority: 'https://login.microsoftonline.com/a66a44bf-bf04-4606-839d-3f956853233b', // Replace with your Tenant ID
    redirectUri: 'http://localhost:4200',
    postLogoutRedirectUri: 'http://localhost:4200',
  },
  cache: {
    cacheLocation: 'localStorage', // Use localStorage for cache
  },
  system: {
    loggerOptions: {
      loggerCallback: (level, message, containsPii) => {
        if (!containsPii) {
          console.log(message);
        }
      },
      logLevel: LogLevel.Warning,
      piiLoggingEnabled: false,
    },
  },
};

/**
 * Scopes for API access
 */
export const loginRequest = {
  scopes: [
    'openid',
    'profile',
    'email',
    'api://28c90a4e-4a96-4f78-ab0e-171bd1a984ba/user_impersonation'
  ],
};

/**
 * API Configuration
 */
export const apiConfig = {
  backendUrl: 'http://localhost:8000', // FastAPI backend URL
  endpoints: {
    tablesServicePrincipal: '/tables',
    tablesUserAuth: '/tables-as-user',
  },
};
