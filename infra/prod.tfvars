# ==============================================================================
# Production Environment Configuration (prod.tfvars)
# ==============================================================================

location     = "eastus"
environment  = "prod"
project_name = "snowflake"

# Naming Convention Overrides for Production
resource_group_name           = "rg-snowflake-prod"
app_service_plan_name         = "asp-snowflake-prod"
app_service_name              = "app-snowflake-prod"
function_app_name             = "func-snowflake-prod"
storage_account_name          = "stsnowflakeprod"
log_analytics_workspace_name  = "log-snowflake-prod"
app_gateway_name              = "agw-snowflake-prod"
data_collection_endpoint_name = "dce-snowflake-prod"
data_collection_rule_name     = "dcr-snowflake-prod"
action_group_name             = "ag-snowflake-prod"

# Existing VNet and Subnet Details
vnet_name                = "vnet-prod-eastus"
vnet_resource_group_name = "rg-network-prod"
agw_subnet_name          = "snet-agw"
pe_subnet_name           = "snet-pe"
app_subnet_name          = "snet-app" # Shared outbound subnet for Web App & Function App

# Application Gateway Private Listener IP
agw_private_ip_address = "10.2.1.10"
agw_sku_name           = "Standard_v2"
agw_sku_tier           = "Standard_v2"
agw_capacity           = 3

# Compute Settings
app_service_plan_sku = "P2v3"
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

# Email addresses for alerts in Production
alert_email_addresses = [
  "prod-alerts@example.com",
  "oncall@example.com"
]

tags = {
  Environment = "prod"
  Project     = "snowflake"
  ManagedBy   = "Terraform"
}
