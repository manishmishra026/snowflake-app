import os
import logging
import time
import hashlib
import queue
import threading
from typing import Any, Optional, Dict, Tuple
import snowflake.connector
from fastapi import HTTPException, status, Request
from app.core.config import settings
from app.db.security import get_user_snowflake_connection, refresh_azure_snowflake_token

logger = logging.getLogger("app")

# Thread-safe locks for synchronization
_pools_lock = threading.Lock()
_user_connections_lock = threading.Lock()

# Global connection pools mapped by auth flow type: { flow: SimpleConnectionPool }
_connection_pools: Dict[str, "SimpleConnectionPool"] = {}

# User OBO connection cache: { token_hash: (conn_object, expires_at) }
_user_connections: Dict[str, Tuple[Any, float]] = {}


class CachedConnectionProxy:
    """Wrapper that prevents closing cached connections when endpoint requests close."""
    def __init__(self, real_conn: Any):
        self._real_conn = real_conn

    def cursor(self, *args, **kwargs) -> Any:
        return self._real_conn.cursor(*args, **kwargs)

    def close(self) -> None:
        # Do not close the cached connection; keep it alive in cache
        pass

    def is_closed(self) -> bool:
        return self._real_conn.is_closed()

    def __getattr__(self, name: str) -> Any:
        return getattr(self._real_conn, name)


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


def _handle_connection_error(flow_name: str, exc: Exception) -> None:
    logger.error("Snowflake connection failed using %s flow: %s", flow_name, exc, exc_info=True)
    if isinstance(exc, (snowflake.connector.DatabaseError, snowflake.connector.ProgrammingError)):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Database connection failed ({flow_name})",
        )
    raise HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail=f"Unable to connect to database using {flow_name} credentials",
    )


def get_snowflake_connection() -> Any:
    """Create a standalone Snowflake connection using Azure Service Principal OAuth token."""
    try:
        token = refresh_azure_snowflake_token()
        connection_params = {
            "account": settings.SNOWFLAKE_ACCOUNT,
            "authenticator": "oauth",
            "token": token,
        }

        if settings.SNOWFLAKE_WAREHOUSE:
            connection_params["warehouse"] = settings.SNOWFLAKE_WAREHOUSE

        if settings.SNOWFLAKE_ROLE:
            connection_params["role"] = settings.SNOWFLAKE_ROLE

        conn = snowflake.connector.connect(**connection_params)
        _setup_database_session(conn, settings.SNOWFLAKE_DATABASE, settings.SNOWFLAKE_SCHEMA)
        return conn
    except Exception as exc:
        _handle_connection_error("Service Principal", exc)


def get_service_account_connection() -> Any:
    """Create a standalone Snowflake connection using Service Account credentials."""
    try:
        user = settings.SNOWFLAKE_SERVICE_ACCOUNT_USER.strip()
        password = settings.SNOWFLAKE_SERVICE_ACCOUNT_PASSWORD.strip()
        role = settings.SNOWFLAKE_SERVICE_ACCOUNT_ROLE.strip()

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
        elif settings.SNOWFLAKE_ROLE:
            connection_params["role"] = settings.SNOWFLAKE_ROLE

        conn = snowflake.connector.connect(**connection_params)
        _setup_database_session(conn, settings.SNOWFLAKE_DATABASE, settings.SNOWFLAKE_SCHEMA)
        return conn
    except Exception as exc:
        _handle_connection_error("Service Account", exc)


def get_pooled_connection(flow: str) -> Any:
    """Retrieve a connection from a shared global pool for service flows."""
    global _connection_pools
    
    with _pools_lock:
        if flow not in _connection_pools:
            def connection_creator():
                connection_params = {
                    "account": settings.SNOWFLAKE_ACCOUNT,
                }
                if settings.SNOWFLAKE_WAREHOUSE:
                    connection_params["warehouse"] = settings.SNOWFLAKE_WAREHOUSE
                    
                if flow == "service-account":
                    user = settings.SNOWFLAKE_SERVICE_ACCOUNT_USER.strip()
                    password = settings.SNOWFLAKE_SERVICE_ACCOUNT_PASSWORD.strip()
                    role = settings.SNOWFLAKE_SERVICE_ACCOUNT_ROLE.strip()
                    
                    if not password:
                        raise RuntimeError("SNOWFLAKE_SERVICE_ACCOUNT_PASSWORD is not set")
                    
                    connection_params.update({
                        "user": user,
                        "password": password,
                    })
                    if role:
                        connection_params["role"] = role
                    elif settings.SNOWFLAKE_ROLE:
                        connection_params["role"] = settings.SNOWFLAKE_ROLE
                else:  # "service-principal"
                    token = refresh_azure_snowflake_token()
                    connection_params.update({
                        "authenticator": "oauth",
                        "token": token,
                    })
                    if settings.SNOWFLAKE_ROLE:
                        connection_params["role"] = settings.SNOWFLAKE_ROLE
                
                conn = snowflake.connector.connect(**connection_params)
                _setup_database_session(conn, settings.SNOWFLAKE_DATABASE, settings.SNOWFLAKE_SCHEMA)
                return conn
                
            _connection_pools[flow] = SimpleConnectionPool(connection_creator, max_size=5)
            
        pool = _connection_pools[flow]
        
    try:
        return pool.get_connection()
    except Exception as exc:
        _handle_connection_error(f"Pooled {flow}", exc)


def get_cached_user_connection(user_token: str) -> Any:
    """Get or create a cached connection for the user token (OBO flow)."""
    global _user_connections
    
    # Hash the token as cache key to avoid holding raw tokens in key memory
    token_hash = hashlib.sha256(user_token.encode("utf-8")).hexdigest()
    now = time.time()
    
    with _user_connections_lock:
        if token_hash in _user_connections:
            conn, expires_at = _user_connections[token_hash]
            try:
                if now < expires_at and not conn.is_closed():
                    logger.info("Reusing cached user Snowflake database connection")
                    return CachedConnectionProxy(conn)
            except Exception:
                pass
                
            # Clean up dead/expired connection
            try:
                conn.close()
            except Exception:
                pass
            del _user_connections[token_hash]
            
    # Open new physical connection outside lock to avoid blocking other threads/users
    logger.info("Opening new Snowflake database connection for user (OBO)")
    conn = get_user_snowflake_connection(user_token)
    
    with _user_connections_lock:
        # Double check if another thread cached a connection in the meantime
        if token_hash in _user_connections:
            existing_conn, expires_at = _user_connections[token_hash]
            try:
                if now < expires_at and not existing_conn.is_closed():
                    # Close the one we just opened and reuse the existing one
                    try:
                        conn.close()
                    except Exception:
                        pass
                    return CachedConnectionProxy(existing_conn)
            except Exception:
                pass
            
            # If the existing one is invalid or expired, close it
            try:
                existing_conn.close()
            except Exception:
                pass
                
        # Cache the connection for 10 minutes (600 seconds)
        _user_connections[token_hash] = (conn, now + 600)
        
    return CachedConnectionProxy(conn)


# FastAPI Dependency for abstract database connection
def get_db_connection(request: Request) -> Any:
    """FastAPI dependency that returns a connection using pooling or cache."""
    flow = settings.SNOWFLAKE_AUTH_FLOW
    logger.info("Initializing database connection using active flow: %s", flow)

    if flow == "user-auth":
        auth_header = request.headers.get("authorization", "")
        if not auth_header.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing bearer token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        user_token = auth_header[7:]
        return get_cached_user_connection(user_token)
        
    elif flow == "service-account":
        return get_pooled_connection("service-account")
        
    else:  # "service-principal"
        return get_pooled_connection("service-principal")
