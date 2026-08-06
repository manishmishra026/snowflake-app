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

    dynamic "column" {
      for_each = var.custom_log_columns
      content {
        name = column.value.name
        type = column.value.type
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
# Alerts & Monitoring Capabilities
# ==============================================================================

# Metric Alert 1: App Service HTTP 5xx Server Errors (Application Down / Failure)
resource "azurerm_monitor_metric_alert" "app_service_5xx" {
  name                = "alert-${azurerm_linux_web_app.main.name}-http5xx"
  resource_group_name = azurerm_resource_group.main.name
  scopes              = [azurerm_linux_web_app.main.id]
  description         = "Triggers when App Service experiences HTTP 5xx server errors or downtime."
  severity            = 1
  frequency           = "PT1M"
  window_size         = "PT5M"

  criteria {
    metric_namespace = "Microsoft.Web/sites"
    metric_name      = "Http5xx"
    aggregation      = "Total"
    operator         = "GreaterThanOrEqual"
    threshold        = 1
  }

  action {
    action_group_id = azurerm_monitor_action_group.main.id
  }

  tags = var.tags
}

# Metric Alert 2: Application Gateway Unhealthy Host Count
resource "azurerm_monitor_metric_alert" "agw_unhealthy_hosts" {
  name                = "alert-${azurerm_application_gateway.main.name}-unhealthy-hosts"
  resource_group_name = azurerm_resource_group.main.name
  scopes              = [azurerm_application_gateway.main.id]
  description         = "Triggers when Application Gateway detects an unhealthy backend host in the pool."
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

# Metric Alert 3: Function App Execution Errors
resource "azurerm_monitor_metric_alert" "function_app_errors" {
  name                = "alert-${azurerm_linux_function_app.main.name}-function-errors"
  resource_group_name = azurerm_resource_group.main.name
  scopes              = [azurerm_linux_function_app.main.id]
  description         = "Triggers when Function App records execution failure count."
  severity            = 1
  frequency           = "PT1M"
  window_size         = "PT5M"

  criteria {
    metric_namespace = "Microsoft.Web/sites"
    metric_name      = "FunctionExecutionErrors"
    aggregation      = "Total"
    operator         = "GreaterThan"
    threshold        = 0
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
