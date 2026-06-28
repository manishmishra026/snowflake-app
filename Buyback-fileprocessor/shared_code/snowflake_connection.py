import os
import logging
from typing import Any
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
import snowflake.connector
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend

def get_private_key_bytes() -> bytes:
    """Retrieves Snowflake private key from Azure Key Vault."""
    azure_kv_url = os.environ.get("AZURE_KEYVAULT_URL", "").strip()
    secret_name = os.environ.get("SNOWFLAKE_PRIVATE_KEY_SECRET_NAME", "snowflake-private-key").strip()
    
    if not azure_kv_url:
        raise RuntimeError("AZURE_KEYVAULT_URL is not configured. Key Vault is required.")
        
    logging.info(f"Fetching Snowflake private key secret '{secret_name}' from Key Vault: {azure_kv_url}")
    credential = DefaultAzureCredential()
    client = SecretClient(vault_url=azure_kv_url, credential=credential)
    secret = client.get_secret(secret_name)
    private_key_content = secret.value.encode("utf-8")

    # Load PEM and convert to DER format
    p_key = serialization.load_pem_private_key(
        private_key_content,
        password=None,
        backend=default_backend()
    )

    return p_key.private_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )

def _setup_database_session(conn: Any, db: str, schema: str) -> None:
    """Sets database and schema context for the session."""
    try:
        cursor = conn.cursor()
        cursor.execute(f'USE DATABASE "{db}"')
        if schema:
            cursor.execute(f'USE SCHEMA "{schema}"')
    finally:
        cursor.close()

def create_snowflake_connection() -> Any:
    """Creates a Snowflake connection using Service Account credentials with Key Pair Auth."""
    account = os.environ.get("SNOWFLAKE_ACCOUNT")
    user = os.environ.get("SNOWFLAKE_SERVICE_ACCOUNT_USER", "webapp_user").strip()
    role = os.environ.get("SNOWFLAKE_ROLE", "").strip()
    warehouse = os.environ.get("SNOWFLAKE_WAREHOUSE", "").strip()
    db = os.environ.get("SNOWFLAKE_DATABASE")
    schema = os.environ.get("SNOWFLAKE_SCHEMA", "PUBLIC")
    
    private_key_der = get_private_key_bytes()

    connection_params = {
        "account": account,
        "user": user,
        "private_key": private_key_der,
    }

    if warehouse:
        connection_params["warehouse"] = warehouse

    if role:
        connection_params["role"] = role

    logging.info(f"Connecting to Snowflake. Account={account}, User={user}, Role={role}, Warehouse={warehouse}")
    conn = snowflake.connector.connect(**connection_params)
    _setup_database_session(conn, db, schema)
    return conn
