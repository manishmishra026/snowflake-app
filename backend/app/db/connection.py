import logging
import queue
import threading
from typing import Any, Optional
import snowflake.connector
from fastapi import HTTPException, status
from app.core.config import settings

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

    def get_connection(self) -> Any:
        try:
            conn = self._pool.get_nowait()
            if conn.is_closed():
                with self._lock:
                    self._created_count -= 1
                return self.get_connection()
            return PooledConnectionProxy(conn, self)
        except queue.Empty:
            create_new = False
            with self._lock:
                if self._created_count < self._max_size:
                    self._created_count += 1
                    create_new = True
            
            if create_new:
                try:
                    logger.info("Creating new physical connection for pool")
                    conn = self._creator_fn()
                    return PooledConnectionProxy(conn, self)
                except Exception:
                    with self._lock:
                        self._created_count -= 1
                    raise
            
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
    try:
        cursor = conn.cursor()
        cursor.execute(f'USE DATABASE "{db}"')
        if schema:
            cursor.execute(f'USE SCHEMA "{schema}"')
    finally:
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


def create_raw_service_account_connection() -> Any:
    """Create a raw Snowflake connection using Service Account credentials."""
    user = settings.SNOWFLAKE_SERVICE_ACCOUNT_USER.strip()
    password = settings.SNOWFLAKE_SERVICE_ACCOUNT_PASSWORD.strip()
    role = settings.SNOWFLAKE_SERVICE_ACCOUNT_ROLE.strip() or settings.SNOWFLAKE_ROLE.strip()

    if not password:
        raise RuntimeError("SNOWFLAKE_SERVICE_ACCOUNT_PASSWORD env variable is not set")

    connection_params = {
        "account": settings.SNOWFLAKE_ACCOUNT,
        "user": user,
        "password": password,
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
