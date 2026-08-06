# Data source for current subscription (required for Service Health Activity Log Alert scope)
data "azurerm_subscription" "current" {}

# ==============================================================================
# Log Analytics Workspace
# ==============================================================================
resource "azurerm_log_analytics_workspace" "main" {
  name                = local.log_name
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  sku                 = "PerGB2018"
  retention_in_days   = 30

  tags = var.tags
}

# ==============================================================================
# Custom Log Analytics Table (BuybackWebAppAuditLogs_CL)
# Note: Provisioned by Azure Monitor DCR, then retention is configured below.
# ==============================================================================
resource "azurerm_log_analytics_workspace_table" "custom_logs" {
  workspace_id      = azurerm_log_analytics_workspace.main.id
  name              = var.custom_log_table_name
  plan              = "Analytics"
  retention_in_days = var.custom_log_table_retention_in_days

  depends_on = [
    azurerm_monitor_data_collection_rule.main
  ]
}

# ==============================================================================
# Custom Logs Ingestion: Data Collection Endpoint (DCE) & Data Collection Rule (DCR)
# Enables custom log streaming from application code/agents directly to Log Analytics.
# ==============================================================================
resource "azurerm_monitor_data_collection_endpoint" "main" {
  name                          = local.dce_name
  resource_group_name           = azurerm_resource_group.main.name
  location                      = azurerm_resource_group.main.location
  kind                          = "Linux"
  public_network_access_enabled = true

  tags = var.tags
}

resource "azurerm_monitor_data_collection_rule" "main" {
  name                        = local.dcr_name
  resource_group_name         = azurerm_resource_group.main.name
  location                    = azurerm_resource_group.main.location
  data_collection_endpoint_id = azurerm_monitor_data_collection_endpoint.main.id

  destinations {
    log_analytics {
      workspace_resource_id = azurerm_log_analytics_workspace.main.id
      name                  = "la-destination"
    }
  }

  stream_declaration {
    stream_name = var.custom_log_stream_name

    column {
      name = "TimeGenerated"
      type = "datetime"
    }

    dynamic "column" {
      for_each = var.custom_log_columns
      content {
        name = column.value.name
        type = column.value.type == "dynamic" ? "string" : column.value.type
      }
    }
  }

  data_flow {
    streams       = [var.custom_log_stream_name]
    destinations  = ["la-destination"]
    transform_kql = "source"
    output_stream = var.custom_log_stream_name
  }

  tags = var.tags
}

# ==============================================================================
# Monitor Action Group (Email Alerts)
# ==============================================================================
resource "azurerm_monitor_action_group" "main" {
  name                = local.ag_name
  resource_group_name = azurerm_resource_group.main.name
  short_name          = "app-alerts"

  dynamic "email_receiver" {
    for_each = var.alert_email_addresses
    content {
      name                    = "Email-${email_receiver.key}"
      email_address           = email_receiver.value
      use_common_alert_schema = true
    }
  }

  tags = var.tags
}

# ==============================================================================
# Alerts & Monitoring Capabilities (14 Alert Rules per Specification)
# ==============================================================================

# 1. Application Gateway: Failed Requests (> 0 in 5 minutes)
resource "azurerm_monitor_metric_alert" "agw_failed_requests" {
  name                = "alert-${azurerm_application_gateway.main.name}-failed-requests"
  resource_group_name = azurerm_resource_group.main.name
  scopes              = [azurerm_application_gateway.main.id]
  description         = "Metric Alert - Failed Requests > 0 in 5 minutes"
  severity            = 1
  frequency           = "PT1M"
  window_size         = "PT5M"

  criteria {
    metric_namespace = "Microsoft.Network/applicationGateways"
    metric_name      = "FailedRequests"
    aggregation      = "Total"
    operator         = "GreaterThan"
    threshold        = 0
  }

  action {
    action_group_id = azurerm_monitor_action_group.main.id
  }

  tags = var.tags
}

# 2. Application Gateway: High 5xx Errors (Response Status 5xx > 10 in 5 minutes)
resource "azurerm_monitor_metric_alert" "agw_high_5xx" {
  name                = "alert-${azurerm_application_gateway.main.name}-high-5xx"
  resource_group_name = azurerm_resource_group.main.name
  scopes              = [azurerm_application_gateway.main.id]
  description         = "Metric Alert - Response Status 5xx > 10 in 5 minutes"
  severity            = 1
  frequency           = "PT1M"
  window_size         = "PT5M"

  criteria {
    metric_namespace = "Microsoft.Network/applicationGateways"
    metric_name      = "ResponseStatus"
    aggregation      = "Total"
    operator         = "GreaterThan"
    threshold        = 10

    dimension {
      name     = "HttpStatusGroup"
      operator = "Include"
      values   = ["5xx"]
    }
  }

  action {
    action_group_id = azurerm_monitor_action_group.main.id
  }

  tags = var.tags
}

# 3. Application Gateway: Backend Unhealthy (Healthy Host Count below expected threshold < 1)
resource "azurerm_monitor_metric_alert" "agw_backend_unhealthy" {
  name                = "alert-${azurerm_application_gateway.main.name}-backend-unhealthy"
  resource_group_name = azurerm_resource_group.main.name
  scopes              = [azurerm_application_gateway.main.id]
  description         = "Metric Alert - Healthy Host Count below expected threshold (< 1)"
  severity            = 0
  frequency           = "PT1M"
  window_size         = "PT5M"

  criteria {
    metric_namespace = "Microsoft.Network/applicationGateways"
    metric_name      = "UnhealthyHostCount"
    aggregation      = "Average"
    operator         = "GreaterThan"
    threshold        = 0
  }

  action {
    action_group_id = azurerm_monitor_action_group.main.id
  }

  tags = var.tags
}

# 4. Application Gateway: High Backend Response Time (> 5 seconds)
resource "azurerm_monitor_metric_alert" "agw_high_backend_response_time" {
  name                = "alert-${azurerm_application_gateway.main.name}-high-backend-response-time"
  resource_group_name = azurerm_resource_group.main.name
  scopes              = [azurerm_application_gateway.main.id]
  description         = "Metric Alert - Backend Response Time > 5 seconds"
  severity            = 2
  frequency           = "PT1M"
  window_size         = "PT5M"

  criteria {
    metric_namespace = "Microsoft.Network/applicationGateways"
    metric_name      = "BackendLastByteResponseTime"
    aggregation      = "Average"
    operator         = "GreaterThan"
    threshold        = 5
  }

  action {
    action_group_id = azurerm_monitor_action_group.main.id
  }

  tags = var.tags
}

# 5. App Service: HTTP 5xx Errors (HTTP 5xx Count > 10 in 5 minutes)
resource "azurerm_monitor_metric_alert" "app_service_5xx_count" {
  name                = "alert-${azurerm_linux_web_app.main.name}-http5xx-high"
  resource_group_name = azurerm_resource_group.main.name
  scopes              = [azurerm_linux_web_app.main.id]
  description         = "Metric Alert - HTTP 5xx Count > 10 in 5 minutes"
  severity            = 1
  frequency           = "PT1M"
  window_size         = "PT5M"

  criteria {
    metric_namespace = "Microsoft.Web/sites"
    metric_name      = "Http5xx"
    aggregation      = "Total"
    operator         = "GreaterThan"
    threshold        = 10
  }

  action {
    action_group_id = azurerm_monitor_action_group.main.id
  }

  tags = var.tags
}

# 6. Storage Account: Capacity Utilization High (> 80%)
resource "azurerm_monitor_metric_alert" "storage_capacity_high" {
  name                = "alert-${azurerm_storage_account.main.name}-capacity-high"
  resource_group_name = azurerm_resource_group.main.name
  scopes              = [azurerm_storage_account.main.id]
  description         = "Metric Alert - Capacity > 80%"
  severity            = 2
  frequency           = "PT1H"
  window_size         = "PT1H"

  criteria {
    metric_namespace = "Microsoft.Storage/storageAccounts"
    metric_name      = "UsedCapacity"
    aggregation      = "Average"
    operator         = "GreaterThan"
    threshold        = var.storage_capacity_alert_threshold_bytes
  }

  action {
    action_group_id = azurerm_monitor_action_group.main.id
  }

  tags = var.tags
}

# 7. Storage Account: Blob Deletion (Activity Log Alert - Delete Blob Operation Detected)
resource "azurerm_monitor_activity_log_alert" "storage_blob_deletion" {
  name                = "alert-${azurerm_storage_account.main.name}-blob-deletion"
  resource_group_name = azurerm_resource_group.main.name
  location            = "global"
  scopes              = [azurerm_resource_group.main.id]
  description         = "Activity Log Alert - Delete Blob Operation Detected"

  criteria {
    category       = "Administrative"
    operation_name = "Microsoft.Storage/storageAccounts/blobServices/containers/blobs/delete"
  }

  action {
    action_group_id = azurerm_monitor_action_group.main.id
  }

  tags = var.tags
}

# 8. Azure Resources: Resource Deletion (Activity Log Alert - Delete Resource Operation)
resource "azurerm_monitor_activity_log_alert" "resource_deletion" {
  name                = "alert-resource-group-deletion"
  resource_group_name = azurerm_resource_group.main.name
  location            = "global"
  scopes              = [azurerm_resource_group.main.id]
  description         = "Activity Log Alert - Delete Resource Operation"

  criteria {
    category       = "Administrative"
    operation_name = "Microsoft.Resources/subscriptions/resourceGroups/delete"
  }

  action {
    action_group_id = azurerm_monitor_action_group.main.id
  }

  tags = var.tags
}

# 9. Microsoft Defender for Cloud: Security Alert Generated (High Severity Alert Detected)
resource "azurerm_monitor_activity_log_alert" "defender_security_alert" {
  name                = "alert-security-high-severity"
  resource_group_name = azurerm_resource_group.main.name
  location            = "global"
  scopes              = [azurerm_resource_group.main.id]
  description         = "Security Alert - High Severity Alert Detected"

  criteria {
    category = "Security"
  }

  action {
    action_group_id = azurerm_monitor_action_group.main.id
  }

  tags = var.tags
}

# 10, 11, 12. Subscription Cost: Budget 50%, 80%, 100% Reached
resource "azurerm_consumption_budget_resource_group" "main" {
  name              = "budget-${azurerm_resource_group.main.name}"
  resource_group_id = azurerm_resource_group.main.id
  amount            = var.monthly_budget_amount
  time_grain        = "Monthly"

  time_period {
    start_date = formatdate("YYYY-MM-01'T'00:00:00'Z'", timestamp())
  }

  # Budget 50% Reached
  notification {
    enabled        = true
    threshold      = 50
    operator       = "GreaterThanOrEqualTo"
    threshold_type = "Actual"
    contact_emails = var.alert_email_addresses
  }

  # Budget 80% Reached
  notification {
    enabled        = true
    threshold      = 80
    operator       = "GreaterThanOrEqualTo"
    threshold_type = "Actual"
    contact_emails = var.alert_email_addresses
  }

  # Budget 100% Reached
  notification {
    enabled        = true
    threshold      = 100
    operator       = "GreaterThanOrEqualTo"
    threshold_type = "Actual"
    contact_emails = var.alert_email_addresses
  }
}

# 13. Azure Service Health: Service Incident (Active Service Incident)
resource "azurerm_monitor_activity_log_alert" "service_incident" {
  name                = "alert-service-health-incident"
  resource_group_name = azurerm_resource_group.main.name
  location            = "global"
  scopes              = [data.azurerm_subscription.current.id]
  description         = "Service Health Alert - Active Service Incident"

  criteria {
    category = "ServiceHealth"

    service_health {
      events = ["Incident"]
    }
  }

  action {
    action_group_id = azurerm_monitor_action_group.main.id
  }

  tags = var.tags
}

# 14. Azure Service Health: Planned Maintenance (Planned Maintenance Notification)
resource "azurerm_monitor_activity_log_alert" "planned_maintenance" {
  name                = "alert-service-health-planned-maintenance"
  resource_group_name = azurerm_resource_group.main.name
  location            = "global"
  scopes              = [data.azurerm_subscription.current.id]
  description         = "Service Health Alert - Planned Maintenance Notification"

  criteria {
    category = "ServiceHealth"

    service_health {
      events = ["Maintenance"]
    }
  }

  action {
    action_group_id = azurerm_monitor_action_group.main.id
  }

  tags = var.tags
}

# ==============================================================================
# Diagnostic Settings (Forwarding logs to Log Analytics Workspace)
# ==============================================================================

# Diagnostic Settings for App Service
resource "azurerm_monitor_diagnostic_setting" "app_service" {
  name                       = "diag-${azurerm_linux_web_app.main.name}"
  target_resource_id         = azurerm_linux_web_app.main.id
  log_analytics_workspace_id = azurerm_log_analytics_workspace.main.id

  enabled_log {
    category = "AppServiceHTTPLogs"
  }

  enabled_log {
    category = "AppServiceConsoleLogs"
  }

  enabled_log {
    category = "AppServiceAppLogs"
  }

  enabled_metric {
    category = "AllMetrics"
  }
}

# Diagnostic Settings for Application Gateway
resource "azurerm_monitor_diagnostic_setting" "app_gateway" {
  name                       = "diag-${azurerm_application_gateway.main.name}"
  target_resource_id         = azurerm_application_gateway.main.id
  log_analytics_workspace_id = azurerm_log_analytics_workspace.main.id

  enabled_log {
    category = "ApplicationGatewayAccessLog"
  }

  enabled_log {
    category = "ApplicationGatewayPerformanceLog"
  }

  enabled_log {
    category = "ApplicationGatewayFirewallLog"
  }

  enabled_metric {
    category = "AllMetrics"
  }
}

# Diagnostic Settings for Function App
resource "azurerm_monitor_diagnostic_setting" "function_app" {
  name                       = "diag-${azurerm_linux_function_app.main.name}"
  target_resource_id         = azurerm_linux_function_app.main.id
  log_analytics_workspace_id = azurerm_log_analytics_workspace.main.id

  enabled_log {
    category = "FunctionAppLogs"
  }

  enabled_metric {
    category = "AllMetrics"
  }
}
