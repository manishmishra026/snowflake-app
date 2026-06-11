# Snowflake Tables API

A FastAPI application that exposes endpoints to list Snowflake tables. Supports two authentication flows:

1. **Service Principal** (`GET /tables`) — Uses Azure AD client credentials to query Snowflake.
2. **User Authentication** (`GET /tables-as-user`) — Uses Azure AD bearer tokens with the on-behalf-of (OBO) flow to query Snowflake as the authenticated user.

## Requirements

- Python 3.9+
- Azure AD service principal with appropriate Snowflake permissions
- Snowflake account with OAuth integration enabled

## Setup

1. Create a Python virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
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
   uvicorn app.main:app --reload
   ```

## API Endpoints

### `GET /health`
Health check endpoint. No authentication required.

### `GET /tables`
List all tables using service principal credentials. No authentication required.

**Response:**
```json
{
  "tables": [
    {"schema": "PUBLIC", "name": "EMPLOYEES"}
  ],
  "count": 1
}
```

### `GET /tables-as-user`
List tables as the authenticated user. Requires Azure AD bearer token in the `Authorization` header.

```bash
curl -H "Authorization: Bearer <token>" http://localhost:8000/tables-as-user
```

Requires `USER_AUTH_*` environment variables to be configured in `.env`.

## Configuration

All configuration is via environment variables (see `.env.example`):

| Variable | Required | Description |
|----------|----------|-------------|
| `AZURE_TENANT_ID` | Yes | Azure AD tenant ID |
| `AZURE_CLIENT_ID` | Yes | Service principal client ID |
| `AZURE_CLIENT_SECRET` | Yes | Service principal secret |
| `SNOWFLAKE_ACCOUNT` | Yes | Snowflake account identifier |
| `SNOWFLAKE_DATABASE` | Yes | Target database |
| `SNOWFLAKE_APPLICATION_ID_URI` | Yes | Snowflake OAuth application URI |
| `SNOWFLAKE_SCHEMA` | No | Schema (default: `PUBLIC`) |
| `SNOWFLAKE_WAREHOUSE` | No | Warehouse to use |
| `SNOWFLAKE_ROLE` | No | Role to assume |
| `ALLOWED_ORIGINS` | No | Comma-separated CORS origins |
| `ENV` | No | `development` or `production` |

For user authentication, prefix equivalent variables with `USER_AUTH_`.

## Testing

```bash
pytest tests/ -v
```

## Architecture

- **Azure OAuth**: Client credentials flow for service principal, OBO flow for user auth
- **Token Caching**: Access tokens cached for 55 minutes (60-minute expiry)
- **Security Headers**: `X-Content-Type-Options`, `X-Frame-Options`, `X-XSS-Protection`, `Strict-Transport-Security`
- **API Docs**: Auto-generated at `/docs` (Swagger) and `/redoc`

## Production Deployment

- Set `ENV=production`
- Store secrets in Azure Key Vault
- Configure `ALLOWED_ORIGINS` for your frontend domain
- Enable HTTPS/SSL
- Run with multiple workers: `uvicorn app.main:app --workers 4`
- Monitor token refresh failures in application logs
