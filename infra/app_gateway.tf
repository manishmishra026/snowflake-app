# ==============================================================================
# Public IP for Application Gateway Management (v2 requirement)
# ==============================================================================
resource "azurerm_public_ip" "agw" {
  name                = "pip-${local.agw_name}"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  allocation_method   = "Static"
  sku                 = "Standard"

  tags = var.tags
}

# ==============================================================================
# Application Gateway (Listening on Static Private IP Address)
# Redirecting traffic to the App Service backend pool
# ==============================================================================
resource "azurerm_application_gateway" "main" {
  name                = local.agw_name
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location

  sku {
    name     = var.agw_sku_name
    tier     = var.agw_sku_tier
    capacity = var.agw_capacity
  }

  gateway_ip_configuration {
    name      = "agw-ip-config"
    subnet_id = data.azurerm_subnet.agw.id
  }

  # Ports
  frontend_port {
    name = "http-port"
    port = 80
  }

  frontend_port {
    name = "https-port"
    port = 443
  }

  # Public Frontend IP Configuration (Required by App Gateway v2)
  frontend_ip_configuration {
    name                 = "public-frontend-ip"
    public_ip_address_id = azurerm_public_ip.agw.id
  }

  # Private Frontend IP Configuration with Static Private IP
  frontend_ip_configuration {
    name                          = "private-frontend-ip"
    subnet_id                     = data.azurerm_subnet.agw.id
    private_ip_address_allocation = "Static"
    private_ip_address            = var.agw_private_ip_address
  }

  # Backend Pool - Pointing to the App Service Default Hostname
  backend_address_pool {
    name  = "app-service-backend-pool"
    fqdns = [azurerm_linux_web_app.main.default_hostname]
  }

  # Backend HTTP Settings (HTTPS with host header override)
  backend_http_settings {
    name                                = "app-service-http-settings"
    cookie_based_affinity               = "Disabled"
    port                                = 443
    protocol                            = "Https"
    request_timeout                     = 60
    pick_host_name_from_backend_address = true
  }

  # Private HTTP Listener (Listening on static private IP)
  http_listener {
    name                           = "private-http-listener"
    frontend_ip_configuration_name = "private-frontend-ip"
    frontend_port_name             = "http-port"
    protocol                       = "Http"
  }

  # Request Routing Rule (Private Listener -> Backend Settings -> App Service Pool)
  request_routing_rule {
    name                       = "private-routing-rule"
    rule_type                  = "Basic"
    http_listener_name         = "private-http-listener"
    backend_address_pool_name  = "app-service-backend-pool"
    backend_http_settings_name = "app-service-http-settings"
    priority                   = 100
  }

  tags = var.tags
}
