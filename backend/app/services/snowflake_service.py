import logging
from typing import Any, List, Tuple
import snowflake.connector
from fastapi import HTTPException, status
from app.core.queries import LIST_TABLES_QUERY, get_table_data_query
from app.models.schemas import TableInfo, TableDataResponse

logger = logging.getLogger("app")

class SnowflakeService:
    @staticmethod
    def list_tables(conn: Any) -> Tuple[List[TableInfo], int]:
        """Fetch list of base tables in the active database and schema."""
        cursor = conn.cursor()
        try:
            cursor.execute(LIST_TABLES_QUERY)
            rows = cursor.fetchall()
            # Pydantic schemas will serialize schema_name as "schema"
            tables = [TableInfo(schema_name=row[0], name=row[1]) for row in rows]
            return tables, len(tables)
        except Exception as exc:
            logger.error("Failed to list tables from Snowflake: %s", exc)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve table listings",
            ) from exc
        finally:
            cursor.close()

    @classmethod
    def get_table_data(cls, conn: Any, table_name: str, limit: int = 50) -> TableDataResponse:
        """Fetch data dynamically for a given table name.
        
        Validates against database schema table listings to prevent SQL injection.
        """
        # Fetch whitelisted tables to verify existence of requested table
        tables, _ = cls.list_tables(conn)
        whitelisted_names = {t.name.upper() for t in tables}
        
        target_table = table_name.upper()
        if target_table not in whitelisted_names:
            logger.warning("Dynamic query blocked: Table '%s' not in schema whitelist", table_name)
            return TableDataResponse(
                success=False,
                table_name=table_name,
                error=f"Table '{table_name}' not found or access is restricted"
            )

        # Run dynamic query safely
        cursor = conn.cursor()
        try:
            query = get_table_data_query(target_table, limit)
            cursor.execute(query)
            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            data = [dict(zip(columns, row)) for row in rows]
            return TableDataResponse(
                success=True,
                table_name=table_name,
                data=data,
                columns=columns
            )
        except snowflake.connector.ProgrammingError as exc:
            err_msg = str(exc)
            logger.warning("Access to table '%s' failed: %s", table_name, err_msg)
            return TableDataResponse(
                success=False,
                table_name=table_name,
                error=f"User does not have access to table '{table_name}'"
            )
        except Exception as exc:
            logger.error("Failed to retrieve table data for '%s': %s", table_name, exc)
            return TableDataResponse(
                success=False,
                table_name=table_name,
                error="Internal server error fetching table data"
            )
        finally:
            cursor.close()
