# ==============================================================================
# General & Environment Variables
# ==============================================================================
variable "location" {
  type        = string
  description = "Azure region where resources will be deployed."
  default     = "canadacentral"
}

variable "environment" {
  type        = string
  description = "Deployment environment (e.g. dev, uat, prod)."
  default     = "dev"
}

variable "project_name" {
  type        = string
  description = "Project name used for naming convention defaults."
  default     = "myapp"
}

variable "tags" {
  type        = map(string)
  description = "Tags to apply to all deployed Azure resources."
  default = {
    Environment = "dev"
    ManagedBy   = "Terraform"
  }
}

# ==============================================================================
# Resource Naming Convention Overrides / Variables
# ==============================================================================
variable "resource_group_name" {
  type        = string
  description = "Name of the main application resource group. If blank, standard naming convention (rg-<project>-<env>) is used."
  default     = ""
}

variable "monitoring_resource_group_name" {
  type        = string
  description = "Name of the dedicated logging and monitoring resource group. If blank, standard naming convention (rg-<project>-<env>-monitoring) is used."
  default     = ""
}

variable "app_service_plan_name" {
  type        = string
  description = "Name of the App Service Plan. If blank, standard convention (asp-<project>-<env>) is used."
  default     = ""
}

variable "app_service_name" {
  type        = string
  description = "Name of the App Service. If blank, standard convention (app-<project>-<env>) is used."
  default     = ""
}

variable "function_app_name" {
  type        = string
  description = "Name of the Function App. If blank, standard convention (func-<project>-<env>) is used."
  default     = ""
}

variable "storage_account_name" {
  type        = string
  description = "Name of the Storage Account (alphanumeric only). If blank, standard convention (st<project><env>) is used."
  default     = ""
}

variable "log_analytics_workspace_name" {
  type        = string
  description = "Name of the Log Analytics Workspace. If blank, standard convention (log-<project>-<env>) is used."
  default     = ""
}

variable "app_gateway_name" {
  type        = string
  description = "Name of the Application Gateway. If blank, standard convention (agw-<project>-<env>) is used."
  default     = ""
}

variable "data_collection_endpoint_name" {
  type        = string
  description = "Name of the Data Collection Endpoint. If blank, standard convention (dce-<project>-<env>) is used."
  default     = ""
}

variable "data_collection_rule_name" {
  type        = string
  description = "Name of the Data Collection Rule. If blank, standard convention (dcr-<project>-<env>) is used."
  default     = ""
}

variable "action_group_name" {
  type        = string
  description = "Name of the Monitor Action Group. If blank, standard convention (ag-<project>-<env>) is used."
  default     = ""
}

# ==============================================================================
# Existing Networking Variables (VNet & Subnets)
# ==============================================================================
variable "vnet_name" {
  type        = string
  description = "Name of the existing Virtual Network provided by user."
}

variable "vnet_resource_group_name" {
  type        = string
  description = "Resource group name where the existing VNet resides."
}

variable "agw_subnet_name" {
  type        = string
  description = "Subnet name dedicated to Application Gateway within the existing VNet."
}

variable "pe_subnet_name" {
  type        = string
  description = "Subnet name dedicated to Private Endpoints within the existing VNet."
}

variable "app_subnet_name" {
  type        = string
  description = "Subnet name dedicated to App Service & Function App outbound VNet Integration (snet_app) within the existing VNet."
  default     = "snet-app"
}

variable "func_subnet_name" {
  type        = string
  description = "Optional override for Function App subnet name if different from snet_app."
  default     = ""
}

# ==============================================================================
# Application Gateway Settings
# ==============================================================================
variable "agw_private_ip_address" {
  type        = string
  description = "Static private IP address for the Application Gateway private listener."
}

variable "agw_sku_name" {
  type        = string
  description = "Application Gateway SKU name (e.g., Standard_v2 or WAF_v2)."
  default     = "Standard_v2"
}

variable "agw_sku_tier" {
  type        = string
  description = "Application Gateway SKU tier (e.g., Standard_v2 or WAF_v2)."
  default     = "Standard_v2"
}

variable "agw_capacity" {
  type        = number
  description = "Capacity (instance count) for Application Gateway."
  default     = 2
}

# ==============================================================================
# Compute Settings (App Service & Function App)
# ==============================================================================
variable "app_service_plan_sku" {
  type        = string
  description = "App Service Plan SKU size. Default set to Premium SKU P1v3 per requirements."
  default     = "P1v3"
}

variable "python_version" {
  type        = string
  description = "Python version for Web App and Function App (Python 3.12)."
  default     = "3.12"
}

# ==============================================================================
# Monitoring & Custom Log Collection Variables (DCE / DCR)
# ==============================================================================
variable "custom_log_table_name" {
  type        = string
  description = "Log Analytics custom table name ending in _CL (e.g., BuybackWebAppAuditLogs_CL)."
  default     = "BuybackWebAppAuditLogs_CL"
}

variable "custom_log_stream_name" {
  type        = string
  description = "Custom log stream name for Data Collection Rule (e.g., Custom-BuybackWebAppAuditLogs_CL)."
  default     = "Custom-BuybackWebAppAuditLogs_CL"
}

variable "custom_log_table_retention_in_days" {
  type        = number
  description = "Data retention period in days for the custom Log Analytics table (1 year = 365 days)."
  default     = 365
}

variable "custom_log_columns" {
  type = list(object({
    name = string
    type = string
  }))
  description = "Schema definitions for custom application log stream sent via DCE/DCR."
  default = [
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
}

# ==============================================================================
# Alerts & Notification Variables
# ==============================================================================
variable "alert_email_addresses" {
  type        = list(string)
  description = "List of email addresses to receive alert notifications via Action Group."
  default     = []
}

variable "monthly_budget_amount" {
  type        = number
  description = "Monthly budget amount for cost alerting (50%, 80%, 100% threshold notifications)."
  default     = 500
}

variable "storage_capacity_alert_threshold_bytes" {
  type        = number
  description = "Storage capacity alert threshold in bytes (default 80GB = 85899345920 bytes)."
  default     = 85899345920
}
