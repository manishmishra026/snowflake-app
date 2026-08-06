import logging
import queue
import threading
from typing import Any, Optional
import snowflake.connector
from fastapi import HTTPException, status
from app.core.config import settings
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

logger = logging.getLogger("app")

# Thread-safe lock for pool initialization
_pool_lock = threading.Lock()

# Global connection pool for service account connections
_connection_pool: Optional["SimpleConnectionPool"] = None


class PooledConnectionProxy:
    """Wrapper that returns the connection back to the pool instead of closing it."""
    def __init__(self, real_conn: Any, pool: "SimpleConnectionPool"):
        self._real_conn = real_conn
        self._pool = pool

    def cursor(self, *args, **kwargs) -> Any:
        return self._real_conn.cursor(*args, **kwargs)

    def close(self) -> None:
        self._pool.release_connection(self._real_conn)

    def is_closed(self) -> bool:
        return self._real_conn.is_closed()

    def __getattr__(self, name: str) -> Any:
        return getattr(self._real_conn, name)


class SimpleConnectionPool:
    """Custom, thread-safe lightweight database connection pool."""
    def __init__(self, creator_fn: Any, max_size: int = 5):
        self._creator_fn = creator_fn
        self._max_size = max_size
        self._pool: queue.Queue = queue.Queue(maxsize=max_size)
        self._lock = threading.Lock()
        self._created_count = 0

    def _try_get_existing_connection(self) -> Optional[Any]:
        """Tries to get a connection from the queue without blocking."""
        try:
            conn = self._pool.get_nowait()
            if conn.is_closed():
                with self._lock:
                    self._created_count -= 1
                return self.get_connection()
            return PooledConnectionProxy(conn, self)
        except queue.Empty:
            return None

    def _create_new_connection(self) -> Optional[Any]:
        """Creates a new database connection if pool limit has not been reached."""
        create_new = False
        with self._lock:
            if self._created_count < self._max_size:
                self._created_count += 1
                create_new = True
        
        if not create_new:
            return None

        try:
            logger.info("Creating new physical connection for pool")
            conn = self._creator_fn()
            return PooledConnectionProxy(conn, self)
        except Exception:
            with self._lock:
                self._created_count -= 1
            raise

    def _wait_for_connection(self) -> Any:
        """Blocks waiting for an available connection from the pool."""
        try:
            conn = self._pool.get(timeout=10.0)
            if conn.is_closed():
                with self._lock:
                    self._created_count -= 1
                return self.get_connection()
            return PooledConnectionProxy(conn, self)
        except queue.Empty:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database connection pool exhausted"
            )

    def get_connection(self) -> Any:
        """Acquires a pooled connection, blocking if the pool limit is reached."""
        conn = self._try_get_existing_connection()
        if conn is not None:
            return conn

        conn = self._create_new_connection()
        if conn is not None:
            return conn

        return self._wait_for_connection()

    def release_connection(self, conn: Any) -> None:
        if conn.is_closed():
            with self._lock:
                self._created_count -= 1
            return
            
        try:
            self._pool.put_nowait(conn)
        except queue.Full:
            try:
                conn.close()
            except Exception:
                pass
            with self._lock:
                self._created_count -= 1


def _setup_database_session(conn: Any, db: str, schema: str) -> None:
    cursor = None
    try:
        cursor = conn.cursor()
        cursor.execute(f'USE DATABASE "{db}"')
        if schema:
            cursor.execute(f'USE SCHEMA "{schema}"')
    finally:
        if cursor:
            cursor.close()


def _handle_connection_error(exc: Exception) -> None:
    logger.error("Snowflake connection failed using Service Account flow: %s", exc, exc_info=True)
    if isinstance(exc, (snowflake.connector.DatabaseError, snowflake.connector.ProgrammingError)):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Database connection failed (Service Account)",
        )
    raise HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail="Unable to connect to database using Service Account credentials",
    )


def get_private_key_bytes() -> bytes:
    """Retrieves Snowflake private key from Key Vault."""
    if not settings.AZURE_KEYVAULT_URL.strip():
        raise RuntimeError("AZURE_KEYVAULT_URL is not configured. Key Vault is required.")
        
    logger.info("Fetching Snowflake private key from Azure Key Vault")
    credential = DefaultAzureCredential()
    client = SecretClient(vault_url=settings.AZURE_KEYVAULT_URL.strip(), credential=credential)
    secret = client.get_secret(settings.SNOWFLAKE_PRIVATE_KEY_SECRET_NAME)
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


def create_raw_service_account_connection() -> Any:
    """Create a raw Snowflake connection using Service Account credentials with Key Pair Auth."""
    user = settings.SNOWFLAKE_SERVICE_ACCOUNT_USER.strip()
    role = settings.SNOWFLAKE_ROLE.strip()
    
    private_key_der = get_private_key_bytes()

    connection_params = {
        "account": settings.SNOWFLAKE_ACCOUNT,
        "user": user,
        "private_key": private_key_der,
    }

    if settings.SNOWFLAKE_WAREHOUSE:
        connection_params["warehouse"] = settings.SNOWFLAKE_WAREHOUSE

    if role:
        connection_params["role"] = role

    conn = snowflake.connector.connect(**connection_params)
    _setup_database_session(conn, settings.SNOWFLAKE_DATABASE, settings.SNOWFLAKE_SCHEMA)
    return conn


def get_db_connection() -> Any:
    """FastAPI dependency that returns a pooled Snowflake connection using Service Account credentials."""
    global _connection_pool
    
    with _pool_lock:
        if _connection_pool is None:
            logger.info("Initializing global database connection pool for service-account flow")
            _connection_pool = SimpleConnectionPool(create_raw_service_account_connection, max_size=5)
            
    try:
        return _connection_pool.get_connection()
    except Exception as exc:
        _handle_connection_error(exc)
