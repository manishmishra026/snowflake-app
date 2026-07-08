import json
import snowflake.connector

with open(r"Buyback-fileprocessor/local.settings.json") as f:
    config = json.load(f)["Values"]

conn = snowflake.connector.connect(
    account=config["SNOWFLAKE_ACCOUNT"],
    user=config["SNOWFLAKE_SERVICE_ACCOUNT_USER"],
    password=config["SNOWFLAKE_SERVICE_ACCOUNT_PASSWORD"],
    role=config.get("SNOWFLAKE_SERVICE_ACCOUNT_ROLE") or config.get("SNOWFLAKE_ROLE"),
    warehouse=config["SNOWFLAKE_WAREHOUSE"]
)
cursor = conn.cursor()

databases = ["SNOWFLAKE_SAMPLE_Apps", "SNOWFLAKE_SAMPLE_DATA"]
target_tables = ["CFA_TRANSCODED", "REFERENCIAL_DATA_UCDM", "BB_LEGAL_ENTITY", "ENT_UC_STOCK_IMAGE"]

for db in databases:
    print(f"\nChecking database: {db}")
    try:
        cursor.execute(f'SHOW SCHEMAS IN DATABASE "{db}"')
        schemas = [row[1] for row in cursor.fetchall()]
        for schema in schemas:
            if schema == "INFORMATION_SCHEMA":
                continue
            try:
                cursor.execute(f'SHOW TABLES IN SCHEMA "{db}"."{schema}"')
                tables = [row[1].upper() for row in cursor.fetchall()]
                for target in target_tables:
                    if target in tables:
                        print(f"  -> Found {target} in schema: {schema}")
            except Exception as e:
                print(f"  Error reading schema {schema}: {e}")
    except Exception as e:
        print(f"Error reading database {db}: {e}")

cursor.close()
conn.close()
