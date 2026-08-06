output "resource_group_name" {
  description = "The name of the Resource Group created."
  value       = azurerm_resource_group.main.name
}

output "app_service_plan_id" {
  description = "The ID of the Premium App Service Plan."
  value       = azurerm_service_plan.main.id
}

output "app_service_name" {
  description = "The name of the Linux Web App."
  value       = azurerm_linux_web_app.main.name
}

output "app_service_default_hostname" {
  description = "The default hostname of the App Service."
  value       = azurerm_linux_web_app.main.default_hostname
}

output "function_app_name" {
  description = "The name of the Linux Function App."
  value       = azurerm_linux_function_app.main.name
}

output "function_app_default_hostname" {
  description = "The default hostname of the Function App."
  value       = azurerm_linux_function_app.main.default_hostname
}

output "storage_account_name" {
  description = "The name of the secure Storage Account."
  value       = azurerm_storage_account.main.name
}

output "storage_account_id" {
  description = "The Resource ID of the Storage Account."
  value       = azurerm_storage_account.main.id
}

output "app_gateway_name" {
  description = "The name of the Application Gateway."
  value       = azurerm_application_gateway.main.name
}

output "app_gateway_private_ip" {
  description = "The static private IP address of the Application Gateway listener."
  value       = var.agw_private_ip_address
}

output "log_analytics_workspace_id" {
  description = "The ID of the Log Analytics Workspace."
  value       = azurerm_log_analytics_workspace.main.id
}

output "log_analytics_workspace_name" {
  description = "The name of the Log Analytics Workspace."
  value       = azurerm_log_analytics_workspace.main.name
}

output "data_collection_endpoint_id" {
  description = "The Resource ID of the Data Collection Endpoint."
  value       = azurerm_monitor_data_collection_endpoint.main.id
}

output "data_collection_endpoint_immutable_id" {
  description = "The immutable ID of the Data Collection Endpoint."
  value       = azurerm_monitor_data_collection_endpoint.main.immutable_id
}

output "data_collection_endpoint_logs_ingestion_uri" {
  description = "Logs Ingestion URI for the Data Collection Endpoint."
  value       = azurerm_monitor_data_collection_endpoint.main.logs_ingestion_endpoint
}

output "data_collection_rule_id" {
  description = "The Resource ID of the Data Collection Rule."
  value       = azurerm_monitor_data_collection_rule.main.id
}

output "data_collection_rule_immutable_id" {
  description = "The immutable ID of the Data Collection Rule."
  value       = azurerm_monitor_data_collection_rule.main.immutable_id
}

output "action_group_id" {
  description = "The ID of the Monitor Action Group for email alerts."
  value       = azurerm_monitor_action_group.main.id
}
