# Variables for GCP Terraform Configuration

variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "region" {
  description = "GCP region"
  type        = string
  default     = "us-central1"
}

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

# Network Configuration
variable "subnet_cidr" {
  description = "CIDR for the subnet"
  type        = string
  default     = "10.0.0.0/24"
}

variable "pods_cidr" {
  description = "CIDR for pods"
  type        = string
  default     = "10.1.0.0/16"
}

variable "services_cidr" {
  description = "CIDR for services"
  type        = string
  default     = "10.2.0.0/16"
}

# GKE Configuration
variable "release_channel" {
  description = "GKE release channel (RAPID, REGULAR, STABLE)"
  type        = string
  default     = "REGULAR"
}

# General Node Pool
variable "general_machine_type" {
  description = "Machine type for general nodes"
  type        = string
  default     = "n1-standard-4"
}

variable "general_node_count_per_zone" {
  description = "Initial node count per zone for general pool"
  type        = number
  default     = 1
}

variable "general_node_min_count" {
  description = "Minimum nodes in general pool"
  type        = number
  default     = 3
}

variable "general_node_max_count" {
  description = "Maximum nodes in general pool"
  type        = number
  default     = 10
}

# GPU Node Pool
variable "gpu_machine_type" {
  description = "Machine type for GPU nodes"
  type        = string
  default     = "n1-standard-4"
}

variable "gpu_type" {
  description = "GPU type (nvidia-tesla-t4, nvidia-tesla-v100, etc.)"
  type        = string
  default     = "nvidia-tesla-t4"
}

variable "gpu_count_per_node" {
  description = "Number of GPUs per node"
  type        = number
  default     = 1
}

variable "gpu_node_count_per_zone" {
  description = "Initial GPU node count per zone"
  type        = number
  default     = 1
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

# Database
variable "enable_cloud_sql" {
  description = "Enable Cloud SQL PostgreSQL"
  type        = bool
  default     = true
}

variable "db_tier" {
  description = "Cloud SQL tier"
  type        = string
  default     = "db-custom-2-8192"  # 2 vCPU, 8GB RAM
}

variable "db_disk_size" {
  description = "Database disk size in GB"
  type        = number
  default     = 50
}

# Cache
variable "enable_memorystore" {
  description = "Enable Memorystore Redis"
  type        = bool
  default     = true
}

variable "redis_tier" {
  description = "Redis tier (BASIC or STANDARD_HA)"
  type        = string
  default     = "STANDARD_HA"
}

variable "redis_memory_gb" {
  description = "Redis memory in GB"
  type        = number
  default     = 5
}

# Encryption
variable "enable_cmek" {
  description = "Enable Customer-Managed Encryption Keys"
  type        = bool
  default     = false
}
