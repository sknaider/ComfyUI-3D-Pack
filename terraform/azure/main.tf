# Terraform Configuration for Azure Deployment
# Creates AKS cluster, Storage Accounts, and related infrastructure

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.23"
    }
  }

  backend "azurerm" {
    resource_group_name  = "terraform-state-rg"
    storage_account_name = "comfyuiterraformstate"
    container_name       = "tfstate"
    key                  = "azure/terraform.tfstate"
  }
}

provider "azurerm" {
  features {
    resource_group {
      prevent_deletion_if_contains_resources = var.environment == "prod" ? true : false
    }
  }
}

# Resource Group
resource "azurerm_resource_group" "main" {
  name     = "${var.project_name}-${var.environment}-rg"
  location = var.location

  tags = {
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "Terraform"
  }
}

# Virtual Network
resource "azurerm_virtual_network" "main" {
  name                = "${var.project_name}-vnet"
  address_space       = [var.vnet_address_space]
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name

  tags = azurerm_resource_group.main.tags
}

# Subnet for AKS
resource "azurerm_subnet" "aks" {
  name                 = "${var.project_name}-aks-subnet"
  resource_group_name  = azurerm_resource_group.main.name
  virtual_network_name = azurerm_virtual_network.main.name
  address_prefixes     = [var.aks_subnet_address_prefix]
}

# AKS Cluster
resource "azurerm_kubernetes_cluster" "main" {
  name                = "${var.project_name}-aks-${var.environment}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  dns_prefix          = "${var.project_name}-${var.environment}"
  kubernetes_version  = var.kubernetes_version

  # Default node pool (system)
  default_node_pool {
    name                = "system"
    vm_size             = var.system_node_vm_size
    node_count          = var.system_node_count
    enable_auto_scaling = true
    min_count           = var.system_node_min_count
    max_count           = var.system_node_max_count
    vnet_subnet_id      = azurerm_subnet.aks.id
    os_disk_size_gb     = 100
    os_disk_type        = "Managed"

    tags = azurerm_resource_group.main.tags
  }

  # Identity
  identity {
    type = "SystemAssigned"
  }

  # Network profile
  network_profile {
    network_plugin    = "azure"
    load_balancer_sku = "standard"
    outbound_type     = "loadBalancer"
  }

  # Azure AD integration
  azure_active_directory_role_based_access_control {
    managed                = true
    azure_rbac_enabled     = true
    admin_group_object_ids = var.admin_group_object_ids
  }

  # Monitoring
  oms_agent {
    log_analytics_workspace_id = azurerm_log_analytics_workspace.main.id
  }

  # Auto-upgrade
  automatic_channel_upgrade = var.environment == "prod" ? "stable" : "patch"

  # Maintenance window
  maintenance_window {
    allowed {
      day   = "Sunday"
      hours = [2, 3, 4]
    }
  }

  tags = azurerm_resource_group.main.tags
}

# User node pool (general workloads)
resource "azurerm_kubernetes_cluster_node_pool" "user" {
  name                  = "user"
  kubernetes_cluster_id = azurerm_kubernetes_cluster.main.id
  vm_size               = var.user_node_vm_size
  node_count            = var.user_node_count
  enable_auto_scaling   = true
  min_count             = var.user_node_min_count
  max_count             = var.user_node_max_count
  vnet_subnet_id        = azurerm_subnet.aks.id
  os_disk_size_gb       = 100

  node_labels = {
    role = "user"
  }

  tags = azurerm_resource_group.main.tags
}

# GPU node pool
resource "azurerm_kubernetes_cluster_node_pool" "gpu" {
  name                  = "gpu"
  kubernetes_cluster_id = azurerm_kubernetes_cluster.main.id
  vm_size               = var.gpu_node_vm_size
  node_count            = var.gpu_node_count
  enable_auto_scaling   = true
  min_count             = var.gpu_node_min_count
  max_count             = var.gpu_node_max_count
  vnet_subnet_id        = azurerm_subnet.aks.id
  os_disk_size_gb       = 200

  node_labels = {
    role              = "gpu"
    "nvidia.com/gpu"  = "true"
  }

  node_taints = [
    "nvidia.com/gpu=true:NoSchedule"
  ]

  tags = azurerm_resource_group.main.tags
}

# Storage Account for models
resource "azurerm_storage_account" "models" {
  name                     = "${replace(var.project_name, "-", "")}models${var.environment}"
  resource_group_name      = azurerm_resource_group.main.name
  location                 = azurerm_resource_group.main.location
  account_tier             = "Standard"
  account_replication_type = var.environment == "prod" ? "GRS" : "LRS"
  account_kind             = "StorageV2"

  blob_properties {
    versioning_enabled = true

    delete_retention_policy {
      days = 30
    }
  }

  tags = azurerm_resource_group.main.tags
}

resource "azurerm_storage_container" "models" {
  name                  = "models"
  storage_account_name  = azurerm_storage_account.models.name
  container_access_type = "private"
}

# Storage Account for outputs
resource "azurerm_storage_account" "outputs" {
  name                     = "${replace(var.project_name, "-", "")}outputs${var.environment}"
  resource_group_name      = azurerm_resource_group.main.name
  location                 = azurerm_resource_group.main.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  account_kind             = "StorageV2"

  blob_properties {
    versioning_enabled = true

    delete_retention_policy {
      days = 30
    }
  }

  tags = azurerm_resource_group.main.tags
}

resource "azurerm_storage_container" "outputs" {
  name                  = "outputs"
  storage_account_name  = azurerm_storage_account.outputs.name
  container_access_type = "private"
}

# Azure Database for PostgreSQL (optional)
resource "azurerm_postgresql_flexible_server" "main" {
  count = var.enable_postgresql ? 1 : 0

  name                   = "${var.project_name}-psql-${var.environment}"
  resource_group_name    = azurerm_resource_group.main.name
  location               = azurerm_resource_group.main.location
  version                = "15"
  administrator_login    = "comfyui_admin"
  administrator_password = var.db_admin_password

  storage_mb = var.db_storage_mb
  sku_name   = var.db_sku_name

  backup_retention_days        = var.environment == "prod" ? 30 : 7
  geo_redundant_backup_enabled = var.environment == "prod" ? true : false

  high_availability {
    mode = var.environment == "prod" ? "ZoneRedundant" : "Disabled"
  }

  tags = azurerm_resource_group.main.tags
}

resource "azurerm_postgresql_flexible_server_database" "main" {
  count = var.enable_postgresql ? 1 : 0

  name      = "comfyui"
  server_id = azurerm_postgresql_flexible_server.main[0].id
  charset   = "UTF8"
  collation = "en_US.utf8"
}

# Azure Cache for Redis (optional)
resource "azurerm_redis_cache" "main" {
  count = var.enable_redis ? 1 : 0

  name                = "${var.project_name}-redis-${var.environment}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  capacity            = var.redis_capacity
  family              = var.redis_family
  sku_name            = var.redis_sku_name

  enable_non_ssl_port = false
  minimum_tls_version = "1.2"

  redis_configuration {
    enable_authentication = true
  }

  tags = azurerm_resource_group.main.tags
}

# Container Registry
resource "azurerm_container_registry" "main" {
  name                = "${replace(var.project_name, "-", "")}acr${var.environment}"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  sku                 = var.environment == "prod" ? "Premium" : "Standard"
  admin_enabled       = false

  georeplications = var.environment == "prod" ? [
    {
      location                = "West Europe"
      zone_redundancy_enabled = true
      tags                    = {}
    }
  ] : []

  tags = azurerm_resource_group.main.tags
}

# Role assignment for AKS to pull from ACR
resource "azurerm_role_assignment" "acr_pull" {
  principal_id                     = azurerm_kubernetes_cluster.main.kubelet_identity[0].object_id
  role_definition_name             = "AcrPull"
  scope                            = azurerm_container_registry.main.id
  skip_service_principal_aad_check = true
}

# Log Analytics Workspace
resource "azurerm_log_analytics_workspace" "main" {
  name                = "${var.project_name}-logs-${var.environment}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  sku                 = "PerGB2018"
  retention_in_days   = var.log_retention_days

  tags = azurerm_resource_group.main.tags
}

# Managed Identity for workloads
resource "azurerm_user_assigned_identity" "comfyui" {
  name                = "${var.project_name}-identity"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location

  tags = azurerm_resource_group.main.tags
}

# Role assignment for storage access
resource "azurerm_role_assignment" "storage_models" {
  principal_id         = azurerm_user_assigned_identity.comfyui.principal_id
  role_definition_name = "Storage Blob Data Contributor"
  scope                = azurerm_storage_account.models.id
}

resource "azurerm_role_assignment" "storage_outputs" {
  principal_id         = azurerm_user_assigned_identity.comfyui.principal_id
  role_definition_name = "Storage Blob Data Contributor"
  scope                = azurerm_storage_account.outputs.id
}

# Application Insights for monitoring
resource "azurerm_application_insights" "main" {
  name                = "${var.project_name}-insights-${var.environment}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  workspace_id        = azurerm_log_analytics_workspace.main.id
  application_type    = "web"

  tags = azurerm_resource_group.main.tags
}
