# ==============================================================================
# Storage Account (Network Access Disabled)
# ==============================================================================
resource "azurerm_storage_account" "main" {
  name                     = local.st_name
  resource_group_name      = azurerm_resource_group.main.name
  location                 = azurerm_resource_group.main.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  account_kind             = "StorageV2"

  # Disable all public network access per security requirement
  public_network_access_enabled = false

  # Ensure HTTPS only and minimum TLS 1.2
  https_traffic_only_enabled = true
  min_tls_version            = "TLS1_2"

  tags = var.tags
}

# ==============================================================================
# Private Endpoints for Storage Sub-Resource Types (blob, queue, table, file)
# Note: Private DNS Zone integration is omitted because an existing Azure Policy
# automatically maps DNS records upon Private Endpoint creation.
# ==============================================================================

# Private Endpoint - Blob
resource "azurerm_private_endpoint" "blob" {
  name                = "pe-${azurerm_storage_account.main.name}-blob"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  subnet_id           = data.azurerm_subnet.pe.id

  private_service_connection {
    name                           = "psc-${azurerm_storage_account.main.name}-blob"
    private_connection_resource_id = azurerm_storage_account.main.id
    subresource_names              = ["blob"]
    is_manual_connection           = false
  }

  tags = var.tags
}

# Private Endpoint - Queue
resource "azurerm_private_endpoint" "queue" {
  name                = "pe-${azurerm_storage_account.main.name}-queue"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  subnet_id           = data.azurerm_subnet.pe.id

  private_service_connection {
    name                           = "psc-${azurerm_storage_account.main.name}-queue"
    private_connection_resource_id = azurerm_storage_account.main.id
    subresource_names              = ["queue"]
    is_manual_connection           = false
  }

  tags = var.tags
}

# Private Endpoint - Table
resource "azurerm_private_endpoint" "table" {
  name                = "pe-${azurerm_storage_account.main.name}-table"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  subnet_id           = data.azurerm_subnet.pe.id

  private_service_connection {
    name                           = "psc-${azurerm_storage_account.main.name}-table"
    private_connection_resource_id = azurerm_storage_account.main.id
    subresource_names              = ["table"]
    is_manual_connection           = false
  }

  tags = var.tags
}

# Private Endpoint - File
resource "azurerm_private_endpoint" "file" {
  name                = "pe-${azurerm_storage_account.main.name}-file"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  subnet_id           = data.azurerm_subnet.pe.id

  private_service_connection {
    name                           = "psc-${azurerm_storage_account.main.name}-file"
    private_connection_resource_id = azurerm_storage_account.main.id
    subresource_names              = ["file"]
    is_manual_connection           = false
  }

  tags = var.tags
}
