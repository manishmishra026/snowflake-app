# ==============================================================================
# Pre-Production Environment Configuration (preprod.tfvars)
# ==============================================================================

location     = "eastus"
environment  = "preprod"
project_name = "snowflake"

# Naming Convention Overrides for Preprod
resource_group_name           = "rg-snowflake-preprod"
app_service_plan_name         = "asp-snowflake-preprod"
app_service_name              = "app-snowflake-preprod"
function_app_name             = "func-snowflake-preprod"
storage_account_name          = "stsnowflakepreprod"
log_analytics_workspace_name  = "log-snowflake-preprod"
app_gateway_name              = "agw-snowflake-preprod"
data_collection_endpoint_name = "dce-snowflake-preprod"
data_collection_rule_name     = "dcr-snowflake-preprod"
action_group_name             = "ag-snowflake-preprod"

# Existing VNet and Subnet Details
vnet_name                = "vnet-preprod-eastus"
vnet_resource_group_name = "rg-network-preprod"
agw_subnet_name          = "snet-agw"
pe_subnet_name           = "snet-pe"
app_subnet_name          = "snet-app" # Shared outbound subnet for Web App & Function App

# Application Gateway Private Listener IP
agw_private_ip_address = "10.1.1.10"
agw_sku_name           = "Standard_v2"
agw_sku_tier           = "Standard_v2"
agw_capacity           = 2

# Compute Settings
app_service_plan_sku = "B1"
python_version       = "3.12"

# Monitoring & Custom Log Settings (BuybackWebAppAuditLogs_CL)
custom_log_table_name  = "BuybackWebAppAuditLogs_CL"
custom_log_stream_name = "Custom-BuybackWebAppAuditLogs_CL"

custom_log_columns = [
  { name = "TimeGenerated", type = "datetime" },
  { name = "action_type", type = "string" },
  { name = "actor_email", type = "string" },
  { name = "actor_user_id", type = "string" },
  { name = "actor_user_name", type = "string" },
  { name = "Application", type = "string" },
  { name = "audit_id", type = "string" },
  { name = "correlation_id", type = "string" },
  { name = "cycle_code", type = "string" },
  { name = "details_json", type = "dynamic" },
  { name = "event_timestamp_utc", type = "datetime" },
  { name = "event_timezone", type = "string" },
  { name = "failure_code", type = "string" },
  { name = "failure_message", type = "string" }
]

# Email addresses for alerts in Preprod
alert_email_addresses = [
  "preprod-alerts@example.com"
]

tags = {
  Environment = "preprod"
  Project     = "snowflake"
  ManagedBy   = "Terraform"
}
