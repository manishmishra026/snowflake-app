# ==============================================================================
# Local Naming Logic
# ==============================================================================
locals {
  # Standard prefix / suffix helpers
  name_prefix  = "${var.project_name}-${var.environment}"
  clean_prefix = replace(lower("${var.project_name}${var.environment}"), "/[^a-z0-9]/", "")

  # Explicit or Naming Convention Fallbacks
  rg_name   = var.resource_group_name != "" ? var.resource_group_name : "rg-${local.name_prefix}"
  asp_name  = var.app_service_plan_name != "" ? var.app_service_plan_name : "asp-${local.name_prefix}"
  app_name  = var.app_service_name != "" ? var.app_service_name : "app-${local.name_prefix}"
  func_name = var.function_app_name != "" ? var.function_app_name : "func-${local.name_prefix}"
  st_name   = var.storage_account_name != "" ? var.storage_account_name : substr("st${local.clean_prefix}app", 0, 24)
  log_name  = var.log_analytics_workspace_name != "" ? var.log_analytics_workspace_name : "log-${local.name_prefix}"
  agw_name  = var.app_gateway_name != "" ? var.app_gateway_name : "agw-${local.name_prefix}"
  dce_name  = var.data_collection_endpoint_name != "" ? var.data_collection_endpoint_name : "dce-${local.name_prefix}"
  dcr_name  = var.data_collection_rule_name != "" ? var.data_collection_rule_name : "dcr-${local.name_prefix}"
  ag_name   = var.action_group_name != "" ? var.action_group_name : "ag-${local.name_prefix}"
}

# ==============================================================================
# Resource Group
# ==============================================================================
resource "azurerm_resource_group" "main" {
  name     = local.rg_name
  location = var.location
  tags     = var.tags
}
