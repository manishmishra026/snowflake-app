# Angular Frontend - Snowflake Tables API

This is an Angular application that demonstrates authentication with Azure AD (Microsoft Entra ID) and integration with the Snowflake Tables API backend.

## Features

✅ **Azure AD Authentication** - Login/logout with MSAL (Microsoft Authentication Library)
✅ **Dual API Endpoints** - Call backend using service principal or user credentials
✅ **Service Principal Flow** - Query tables without user authentication
✅ **User Authentication Flow** - Query tables with on-behalf-of (OBO) token exchange
✅ **Responsive UI** - Beautiful, modern interface with loading states and error handling

## Prerequisites

- Node.js 18+ and npm 9+
- Angular 21+
- Backend FastAPI server running on `http://localhost:8000`
- Azure AD tenant and application registration

## Setup Instructions

### 1. Install Dependencies

```bash
cd frontend/snowflake-webapp
npm install
```

### 2. Configure Azure AD

Edit [src/app/config/auth.config.ts](src/app/config/auth.config.ts):

```typescript
export const msalConfig: Configuration = {
  auth: {
    clientId: 'YOUR_CLIENT_ID',           // ← Replace with your App Registration ID
    authority: 'https://login.microsoftonline.com/YOUR_TENANT_ID', // ← Replace with your Tenant ID
    redirectUri: 'http://localhost:4200',
    postLogoutRedirectUri: 'http://localhost:4200',
  },
  ...
};
```

**How to find these values:**

1. Go to [Azure Portal](https://portal.azure.com)
2. Search for "App registrations"
3. Click on your application
4. Copy:
   - **Application (Client) ID** → Use as `clientId`
   - **Directory (Tenant) ID** → Use as `YOUR_TENANT_ID` in authority URL

### 3. Backend Configuration

Ensure your FastAPI backend is running:

```bash
# In the backend folder
cd ../..  # Go back to testconnectivity
python -m uvicorn app.main:app --reload
```

The backend should be accessible at `http://localhost:8000`

**Verify backend is ready:**
```bash
curl http://localhost:8000/health
# Should return: {"status": "ok"}
```

### 4. Run the Frontend

```bash
# Start the development server
npm start
```

The application will be available at `http://localhost:4200`

## Application Structure

```
src/app/
├── config/
│   └── auth.config.ts          # Azure AD and API configuration
├── services/
│   ├── auth.service.ts         # Azure AD authentication (MSAL)
│   └── api.service.ts          # Backend API calls
├── components/
│   └── home/
│       ├── home.component.ts   # Main component
│       ├── home.component.html # Template
│       └── home.component.css  # Styles
├── app.ts                      # Root component
├── app.config.ts               # Angular configuration with MSAL
├── app.routes.ts               # Router configuration
└── app.html                    # Root template
```

## Using the Application

### Login
1. Click **"Login with Azure AD"** button
2. You'll be redirected to Azure AD login
3. Enter your credentials
4. You'll be redirected back to the application
5. Your name will be displayed in the header

### Query Tables - Service Principal Flow
1. Click **"📋 Get Tables (Service Principal)"**
2. Tables are fetched using the backend's service principal credentials
3. No user token required
4. Results show all tables available to the service principal

### Query Tables - User Auth Flow
1. **Must be logged in** (click login first)
2. Click **"👤 Get Tables (User Auth)"**
3. Your Azure AD token is exchanged for a Snowflake token (OBO flow)
4. Results show only tables you have permission to access
5. Snowflake audit logs show query was executed as your user

## API Endpoints

The frontend calls these backend endpoints:

| Endpoint | Method | Auth | Purpose |
|----------|--------|------|---------|
| `/health` | GET | None | Health check |
| `/tables` | GET | None | List tables (service principal) |
| `/tables-as-user` | GET | Bearer | List tables (user auth with OBO) |

### Headers

**For service principal endpoint (`/tables`):**
```
GET http://localhost:8000/tables
```

**For user endpoint (`/tables-as-user`):**
```
GET http://localhost:8000/tables-as-user
Authorization: Bearer <user_azure_ad_token>
```

The frontend automatically handles adding the bearer token using the `ApiService`.

## Environment Configuration

### Frontend (`src/app/config/auth.config.ts`)

```typescript
export const msalConfig: Configuration = {
  auth: {
    clientId: 'YOUR_CLIENT_ID',
    authority: 'https://login.microsoftonline.com/YOUR_TENANT_ID',
    redirectUri: 'http://localhost:4200',
  },
  ...
};

export const apiConfig = {
  backendUrl: 'http://localhost:8000',
  endpoints: {
    tablesServicePrincipal: '/tables',
    tablesUserAuth: '/tables-as-user',
  },
};
```

### Backend (`.env`)

```bash
# Service Principal Flow
AZURE_TENANT_ID=your-tenant-id
AZURE_CLIENT_ID=your-sp-client-id
AZURE_CLIENT_SECRET=your-sp-client-secret
SNOWFLAKE_ACCOUNT=your-account-id
SNOWFLAKE_DATABASE=your-database
SNOWFLAKE_APPLICATION_ID_URI=https://your-account.snowflakecomputing.com

# User Authentication Flow (Optional)
USER_AUTH_AZURE_TENANT_ID=your-tenant-id
USER_AUTH_AZURE_CLIENT_ID=your-client-id
USER_AUTH_AZURE_CLIENT_SECRET=your-client-secret
USER_AUTH_SNOWFLAKE_ACCOUNT=your-account-id
USER_AUTH_SNOWFLAKE_DATABASE=your-database
USER_AUTH_SNOWFLAKE_APPLICATION_ID_URI=https://your-account.snowflakecomputing.com
```

## Development

### Build for production
```bash
npm run build
```

Output will be in `dist/snowflake-webapp/`

### Run tests
```bash
npm run test
```

### Format code (if Prettier is configured)
```bash
npm run format
```

## Troubleshooting

### "Login failed" error
- ❌ Verify `clientId` and `tenantId` are correct in `auth.config.ts`
- ❌ Check Azure App Registration exists and has correct redirect URI
- ❌ Verify browser redirects to Azure AD login page

### "Failed to fetch tables" (Service Principal)
- ❌ Ensure backend is running: `http://localhost:8000/health`
- ❌ Check backend `.env` has all required variables
- ❌ Verify Snowflake connection details are correct

### "Error: Unable to acquire access token" (User Auth)
- ❌ Ensure you're logged in first
- ❌ Verify user has required scopes in Azure AD
- ❌ Check token isn't expired (tokens expire after 1 hour by default)

### "Invalid or expired token" (User Auth)
- ❌ Log out and log back in to refresh token
- ❌ Verify Azure AD JWKS endpoint is accessible
- ❌ Check token audience matches configuration

### CORS Issues
If you see CORS errors in browser console:
- ❌ Backend must have CORS enabled for `http://localhost:4200`
- ❌ Check FastAPI `CORSMiddleware` configuration

## Security Best Practices

✅ **Implemented:**
- Azure AD MSAL authentication with secure token storage
- Bearer token in Authorization header (not in URL)
- Automatic token refresh before expiration
- HTTPS redirect URI configuration
- User context maintained throughout session
- CORS restrictions

⚠️ **For Production:**
- Use HTTPS only
- Store Azure credentials in secure environment variables
- Implement PKCE (Proof Key for Code Exchange)
- Enable refresh tokens
- Add CSP (Content Security Policy) headers
- Implement rate limiting
- Use secure session storage
- Regular security audits

## References

- [MSAL for Angular Documentation](https://github.com/AzureAD/microsoft-authentication-library-for-js)
- [Angular Routing](https://angular.dev/guide/routing)
- [Angular HTTP Client](https://angular.dev/guide/http)
- [Azure AD Documentation](https://learn.microsoft.com/en-us/azure/active-directory/)
- [Snowflake OAuth](https://docs.snowflake.com/en/user-guide/oauth-intro)
