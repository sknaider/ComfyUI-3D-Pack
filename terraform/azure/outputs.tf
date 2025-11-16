# Outputs for Azure Terraform Configuration

# Resource Group Outputs
output "resource_group_name" {
  description = "Resource group name"
  value       = azurerm_resource_group.main.name
}

output "resource_group_location" {
  description = "Resource group location"
  value       = azurerm_resource_group.main.location
}

# Network Outputs
output "vnet_id" {
  description = "Virtual network ID"
  value       = azurerm_virtual_network.main.id
}

output "aks_subnet_id" {
  description = "AKS subnet ID"
  value       = azurerm_subnet.aks.id
}

# AKS Outputs
output "cluster_name" {
  description = "AKS cluster name"
  value       = azurerm_kubernetes_cluster.main.name
}

output "cluster_id" {
  description = "AKS cluster ID"
  value       = azurerm_kubernetes_cluster.main.id
}

output "cluster_fqdn" {
  description = "AKS cluster FQDN"
  value       = azurerm_kubernetes_cluster.main.fqdn
}

output "cluster_endpoint" {
  description = "AKS cluster endpoint"
  value       = azurerm_kubernetes_cluster.main.kube_config[0].host
  sensitive   = true
}

output "cluster_ca_certificate" {
  description = "AKS cluster CA certificate"
  value       = azurerm_kubernetes_cluster.main.kube_config[0].cluster_ca_certificate
  sensitive   = true
}

output "cluster_identity_principal_id" {
  description = "AKS cluster managed identity principal ID"
  value       = azurerm_kubernetes_cluster.main.identity[0].principal_id
}

output "kubelet_identity_object_id" {
  description = "Kubelet managed identity object ID"
  value       = azurerm_kubernetes_cluster.main.kubelet_identity[0].object_id
}

# Storage Outputs
output "models_storage_account_name" {
  description = "Models storage account name"
  value       = azurerm_storage_account.models.name
}

output "models_storage_account_key" {
  description = "Models storage account primary key"
  value       = azurerm_storage_account.models.primary_access_key
  sensitive   = true
}

output "models_container_name" {
  description = "Models container name"
  value       = azurerm_storage_container.models.name
}

output "outputs_storage_account_name" {
  description = "Outputs storage account name"
  value       = azurerm_storage_account.outputs.name
}

output "outputs_storage_account_key" {
  description = "Outputs storage account primary key"
  value       = azurerm_storage_account.outputs.primary_access_key
  sensitive   = true
}

output "outputs_container_name" {
  description = "Outputs container name"
  value       = azurerm_storage_container.outputs.name
}

# Database Outputs
output "postgresql_fqdn" {
  description = "PostgreSQL server FQDN"
  value       = var.enable_postgresql ? azurerm_postgresql_flexible_server.main[0].fqdn : null
}

output "postgresql_database_name" {
  description = "PostgreSQL database name"
  value       = var.enable_postgresql ? azurerm_postgresql_flexible_server_database.main[0].name : null
}

output "postgresql_admin_username" {
  description = "PostgreSQL admin username"
  value       = var.enable_postgresql ? azurerm_postgresql_flexible_server.main[0].administrator_login : null
  sensitive   = true
}

# Redis Outputs
output "redis_hostname" {
  description = "Redis cache hostname"
  value       = var.enable_redis ? azurerm_redis_cache.main[0].hostname : null
}

output "redis_port" {
  description = "Redis cache SSL port"
  value       = var.enable_redis ? azurerm_redis_cache.main[0].ssl_port : null
}

output "redis_primary_key" {
  description = "Redis cache primary key"
  value       = var.enable_redis ? azurerm_redis_cache.main[0].primary_access_key : null
  sensitive   = true
}

# Container Registry Outputs
output "acr_name" {
  description = "Azure Container Registry name"
  value       = azurerm_container_registry.main.name
}

output "acr_login_server" {
  description = "Azure Container Registry login server"
  value       = azurerm_container_registry.main.login_server
}

# Managed Identity Outputs
output "workload_identity_client_id" {
  description = "Workload identity client ID"
  value       = azurerm_user_assigned_identity.comfyui.client_id
}

output "workload_identity_principal_id" {
  description = "Workload identity principal ID"
  value       = azurerm_user_assigned_identity.comfyui.principal_id
}

# Log Analytics Outputs
output "log_analytics_workspace_id" {
  description = "Log Analytics workspace ID"
  value       = azurerm_log_analytics_workspace.main.id
}

output "log_analytics_workspace_key" {
  description = "Log Analytics workspace primary key"
  value       = azurerm_log_analytics_workspace.main.primary_shared_key
  sensitive   = true
}

# Application Insights Outputs
output "application_insights_instrumentation_key" {
  description = "Application Insights instrumentation key"
  value       = azurerm_application_insights.main.instrumentation_key
  sensitive   = true
}

output "application_insights_connection_string" {
  description = "Application Insights connection string"
  value       = azurerm_application_insights.main.connection_string
  sensitive   = true
}

# kubectl Configuration
output "configure_kubectl" {
  description = "Command to configure kubectl"
  value       = "az aks get-credentials --resource-group ${azurerm_resource_group.main.name} --name ${azurerm_kubernetes_cluster.main.name}"
}

# Helm Values Output
output "helm_values" {
  description = "Values for Helm deployment"
  value = {
    region = var.location
    serviceAccount = {
      annotations = {
        "azure.workload.identity/client-id" = azurerm_user_assigned_identity.comfyui.client_id
      }
    }
    objectStorage = {
      enabled            = true
      type               = "azure"
      bucket             = azurerm_storage_container.models.name
      region             = var.location
      connectionString   = azurerm_storage_account.models.primary_connection_string
      storageAccountName = azurerm_storage_account.models.name
    }
    redis = var.enable_redis ? {
      enabled  = true
      host     = azurerm_redis_cache.main[0].hostname
      port     = azurerm_redis_cache.main[0].ssl_port
      password = azurerm_redis_cache.main[0].primary_access_key
      ssl      = true
    } : null
    postgresql = var.enable_postgresql ? {
      enabled  = true
      host     = azurerm_postgresql_flexible_server.main[0].fqdn
      port     = 5432
      database = azurerm_postgresql_flexible_server_database.main[0].name
      username = azurerm_postgresql_flexible_server.main[0].administrator_login
      password = var.db_admin_password
      ssl      = true
    } : null
  }
  sensitive = true
}
