# ==============================================================================
# Data Sources for User-Provided Existing Virtual Network & Subnets
# ==============================================================================

data "azurerm_virtual_network" "existing" {
  name                = var.vnet_name
  resource_group_name = var.vnet_resource_group_name
}

# Subnet for Application Gateway
data "azurerm_subnet" "agw" {
  name                 = var.agw_subnet_name
  virtual_network_name = data.azurerm_virtual_network.existing.name
  resource_group_name  = var.vnet_resource_group_name
}

# Subnet for Private Endpoints (Storage account sub-resources)
data "azurerm_subnet" "pe" {
  name                 = var.pe_subnet_name
  virtual_network_name = data.azurerm_virtual_network.existing.name
  resource_group_name  = var.vnet_resource_group_name
}

# Subnet delegated for App Service and Function App Outbound VNet Integration (snet_app)
data "azurerm_subnet" "app" {
  name                 = var.app_subnet_name
  virtual_network_name = data.azurerm_virtual_network.existing.name
  resource_group_name  = var.vnet_resource_group_name
}
