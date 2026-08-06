# ==============================================================================
# Linux Function App (Python 3.12)
# ==============================================================================
resource "azurerm_linux_function_app" "main" {
  name                       = local.func_name
  resource_group_name        = azurerm_resource_group.main.name
  location                   = azurerm_resource_group.main.location
  service_plan_id            = azurerm_service_plan.main.id
  storage_account_name       = azurerm_storage_account.main.name
  storage_account_access_key = azurerm_storage_account.main.primary_access_key
  virtual_network_subnet_id  = data.azurerm_subnet.app.id
  https_only                 = true

  site_config {
    application_stack {
      python_version = var.python_version # Python 3.12
    }
  }

  app_settings = {
    "FUNCTIONS_WORKER_RUNTIME"       = "python"
    "BUILD_FLAGS"                    = "UseExpressBuild"
    "ENABLE_ORYX_BUILD"              = "true"
    "SCM_DO_BUILD_DURING_DEPLOYMENT" = "1"
    "AzureWebJobsSecretStorageType"  = "files"
  }

  tags = var.tags
}
