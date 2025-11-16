# Variables for Azure Terraform Configuration

variable "project_name" {
  description = "Project name for resource naming"
  type        = string
  default     = "comfyui-3d-pack"
}

variable "environment" {
  description = "Environment (dev, staging, prod)"
  type        = string
  default     = "prod"

  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be dev, staging, or prod."
  }
}

variable "location" {
  description = "Azure region"
  type        = string
  default     = "eastus"
}

# Network Configuration
variable "vnet_address_space" {
  description = "Address space for VNet"
  type        = string
  default     = "10.1.0.0/16"
}

variable "aks_subnet_address_prefix" {
  description = "Address prefix for AKS subnet"
  type        = string
  default     = "10.1.0.0/20"
}

# AKS Configuration
variable "kubernetes_version" {
  description = "Kubernetes version for AKS"
  type        = string
  default     = "1.28"
}

variable "admin_group_object_ids" {
  description = "Azure AD group object IDs for cluster admins"
  type        = list(string)
  default     = []
}

# System Node Pool
variable "system_node_vm_size" {
  description = "VM size for system node pool"
  type        = string
  default     = "Standard_D4s_v3"
}

variable "system_node_count" {
  description = "Initial node count for system pool"
  type        = number
  default     = 3
}

variable "system_node_min_count" {
  description = "Minimum nodes in system pool"
  type        = number
  default     = 2
}

variable "system_node_max_count" {
  description = "Maximum nodes in system pool"
  type        = number
  default     = 10
}

# User Node Pool
variable "user_node_vm_size" {
  description = "VM size for user node pool"
  type        = string
  default     = "Standard_D8s_v3"
}

variable "user_node_count" {
  description = "Initial node count for user pool"
  type        = number
  default     = 3
}

variable "user_node_min_count" {
  description = "Minimum nodes in user pool"
  type        = number
  default     = 2
}

variable "user_node_max_count" {
  description = "Maximum nodes in user pool"
  type        = number
  default     = 20
}

# GPU Node Pool
variable "gpu_node_vm_size" {
  description = "VM size for GPU nodes (Standard_NC6s_v3, Standard_NC12s_v3, etc.)"
  type        = string
  default     = "Standard_NC6s_v3"  # 1x NVIDIA V100
}

variable "gpu_node_count" {
  description = "Initial GPU node count"
  type        = number
  default     = 2
}

variable "gpu_node_min_count" {
  description = "Minimum GPU nodes"
  type        = number
  default     = 2
}

variable "gpu_node_max_count" {
  description = "Maximum GPU nodes"
  type        = number
  default     = 10
}

# Database Configuration
variable "enable_postgresql" {
  description = "Enable Azure Database for PostgreSQL"
  type        = bool
  default     = true
}

variable "db_admin_password" {
  description = "Database admin password"
  type        = string
  sensitive   = true
  default     = ""  # Set via environment or tfvars
}

variable "db_sku_name" {
  description = "Database SKU (GP_Standard_D2s_v3, etc.)"
  type        = string
  default     = "GP_Standard_D2s_v3"
}

variable "db_storage_mb" {
  description = "Database storage in MB"
  type        = number
  default     = 51200  # 50GB
}

# Redis Configuration
variable "enable_redis" {
  description = "Enable Azure Cache for Redis"
  type        = bool
  default     = true
}

variable "redis_capacity" {
  description = "Redis cache capacity (0-6 for Basic/Standard, 1-5 for Premium)"
  type        = number
  default     = 2
}

variable "redis_family" {
  description = "Redis family (C for Basic/Standard, P for Premium)"
  type        = string
  default     = "C"
}

variable "redis_sku_name" {
  description = "Redis SKU (Basic, Standard, Premium)"
  type        = string
  default     = "Standard"

  validation {
    condition     = contains(["Basic", "Standard", "Premium"], var.redis_sku_name)
    error_message = "Redis SKU must be Basic, Standard, or Premium."
  }
}

# Logging
variable "log_retention_days" {
  description = "Log retention in days"
  type        = number
  default     = 30
}
