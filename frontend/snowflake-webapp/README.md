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

### 2. Configure Frontend Environment

All Azure AD MSAL values (Client ID, Tenant ID, Scopes) and Application Insights parameters are loaded **locally** by the frontend from `public/assets/config/config.json` on startup. This ensures that the frontend can bootstrap and configure MSAL before calling the protected backend API.

To configure these parameters, edit or replace the static configuration file `public/assets/config/config.json` (using `config.json.example` as a template):
- `client_id`: Azure AD Client ID (for MSAL frontend user authentication)
- `tenant_id`: Azure AD Tenant ID (for MSAL frontend login authority)
- `scopes`: Scopes to request (e.g. `openid`, `profile`, `email`, and `api://{client_id}/user_impersonation`)
- `auth_flow`: Active authentication flow (e.g. `service-principal`, `user-auth`, `service-account`)
- `app_insights_connection_string`: Azure Application Insights connection string for frontend telemetry logging

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

### Login & Query Tables
1. **Sign In**: Click **"Login with Azure AD"** button and enter your credentials.
2. **Retrieve Tables**: Once signed in, click **"📋 Fetch Database Tables"**. The frontend calls the backend API `/tables`. The backend determines how to connect to Snowflake based on the active `SNOWFLAKE_AUTH_FLOW` configured in `.env` (service-account, service-principal, or user-auth OBO).
3. **View Table Data**: Click on any table card to view columns and records dynamically fetched from `/tables/{table_name}/data`.

## API Endpoints

The frontend calls these backend endpoints:

| Endpoint | Method | Auth | Purpose |
|----------|--------|------|---------|
| `/health` | GET | None | Health check |
| `/tables` | GET | Bearer (Optional) | List Snowflake tables dynamically |
| `/tables/{table_name}/data` | GET | Bearer (Optional) | Fetch dynamic columns and records for a table |

### Headers

If the user is logged into the frontend, requests will automatically include the `Authorization` header containing the user's Entra ID Bearer token:
```
Authorization: Bearer <entra_id_token>
```
If the backend is set to `user-auth` flow, it will exchange this token to query Snowflake on behalf of the user. Otherwise, the backend ignores it and queries using service-account or service-principal credentials.

## Environment Configuration

### Frontend (`public/assets/config/config.json`)

```json
{
  "app_insights_connection_string": "InstrumentationKey=your-guid",
  "client_id": "your-azure-ad-client-id",
  "tenant_id": "your-azure-ad-tenant-id",
  "scopes": [
    "openid",
    "profile",
    "email",
    "api://your-azure-ad-client-id/user_impersonation"
  ],
  "backend_url": "http://localhost:8000"
}
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
