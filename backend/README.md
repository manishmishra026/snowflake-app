# Buyback API

A FastAPI application that exposes endpoints to list and view Snowflake database tables.

## Architecture & Authentication
- **Snowflake Integration**: Uses a thread-safe connection pool authenticated solely via a **Service Account** (username/password credentials).
- **API Security (Bearer Token Validation)**: Endpoints are protected by a code-based Entra ID JWT validator. It parses the incoming Bearer token, downloads JWKS signing keys, validates the signature/issuer, and verifies that the calling client application ID is in the whitelisted `ALLOWED_CLIENT_IDS` (e.g. the Buyback Web App or backend daemon client).
- **Telemetry**: Automatically exports log traces and performance metrics to **Azure Application Insights**.

## Requirements
- Python 3.9+
- Snowflake service account with appropriate read privileges
- Azure AD App Registration (for validating client tokens)

## Setup

1. Create a Python virtual environment:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Configure environment variables:
   ```bash
   cp .env.example .env
   # Edit .env with your Azure AD and Snowflake credentials
   ```

4. Start the API:
   ```bash
   .venv\Scripts\python -m uvicorn app.main:app --reload --port 8000
   ```

## API Endpoints

### `GET /health`
Health check status. No authentication required.

### `GET /config/client-settings`
Returns non-sensitive client configuration settings (such as Tenant ID, Frontend Client ID, Scopes, and App Insights connection string) to the frontend client dynamically on bootstrap. No authentication required.

### `GET /tables`
Lists base tables available in the configured database and schema. **Requires a valid Azure AD bearer token** in the `Authorization` header.

### `GET /tables/{table_name}/data`
Retrieves column schemas and row records dynamically for a table (capped at 50 records). Protects against SQL injection using table whitelisting. **Requires a valid Azure AD bearer token** in the `Authorization` header.

## Testing

Run tests with Pytest:
```bash
.venv\Scripts\python -m pytest
```
