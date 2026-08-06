# ==============================================================================
# Linux App Service Plan (Premium SKU per requirement)
# ==============================================================================
resource "azurerm_service_plan" "main" {
  name                = local.asp_name
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  os_type             = "Linux"
  sku_name            = var.app_service_plan_sku # e.g., P1v3

  tags = var.tags
}

# ==============================================================================
# Linux App Service (Web App - Python 3.12)
# ==============================================================================
resource "azurerm_linux_web_app" "main" {
  name                      = local.app_name
  resource_group_name       = azurerm_resource_group.main.name
  location                  = azurerm_resource_group.main.location
  service_plan_id           = azurerm_service_plan.main.id
  virtual_network_subnet_id = data.azurerm_subnet.app.id
  https_only                = true

  site_config {
    always_on = true

    application_stack {
      python_version = var.python_version # Python 3.12
    }

    # Enable detailed logging & metrics
    http2_enabled = true
  }

  app_settings = {
    "WEBSITE_RUN_FROM_PACKAGE"            = "1"
    "SCM_DO_BUILD_DURING_DEPLOYMENT"      = "true"
    "PYTHON_ENABLE_GUNICORN_MULTIWORKERS" = "true"
  }

  tags = var.tags
}
