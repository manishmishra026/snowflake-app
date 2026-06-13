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
    redirectUri: typeof window !== 'undefined' ? window.location.origin : 'http://localhost:4200',
    postLogoutRedirectUri: typeof window !== 'undefined' ? window.location.origin : 'http://localhost:4200',
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
    'api://89a80661-cf8b-4e10-b3f4-b2b06be53a81/user_impersonation'
  ],
};

/**
 * API Configuration
 */
export const apiConfig = {
  backendUrl: typeof window !== 'undefined'
    ? (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
        ? 'http://localhost:8000'
        : window.location.origin) // Replace with your production backend App Service URL if different
    : 'http://localhost:8000',
  endpoints: {
    tablesServicePrincipal: '/tables',
    tablesUserAuth: '/tables-as-user',
    tablesServiceAccount: '/tables-as-service-account',
    tableDataServiceAccount: '/table-data-as-service-account',
  },
};
