# Terraform Configuration for GCP Deployment
# Creates GKE cluster, Cloud Storage buckets, and related infrastructure

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.23"
    }
  }

  backend "gcs" {
    bucket = "comfyui-terraform-state"
    prefix = "gcp/terraform.tfstate"
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# Data sources
data "google_client_config" "default" {}

data "google_compute_zones" "available" {
  region = var.region
}

# VPC Network
resource "google_compute_network" "vpc" {
  name                    = "${var.project_name}-vpc-${var.environment}"
  auto_create_subnetworks = false
  routing_mode            = "REGIONAL"
}

# Subnet for GKE
resource "google_compute_subnetwork" "subnet" {
  name          = "${var.project_name}-subnet-${var.environment}"
  ip_cidr_range = var.subnet_cidr
  region        = var.region
  network       = google_compute_network.vpc.id

  secondary_ip_range {
    range_name    = "pods"
    ip_cidr_range = var.pods_cidr
  }

  secondary_ip_range {
    range_name    = "services"
    ip_cidr_range = var.services_cidr
  }

  private_ip_google_access = true
}

# Cloud Router and NAT for private nodes
resource "google_compute_router" "router" {
  name    = "${var.project_name}-router-${var.environment}"
  region  = var.region
  network = google_compute_network.vpc.id
}

resource "google_compute_router_nat" "nat" {
  name   = "${var.project_name}-nat-${var.environment}"
  router = google_compute_router.router.name
  region = var.region

  nat_ip_allocate_option             = "AUTO_ONLY"
  source_subnetwork_ip_ranges_to_nat = "ALL_SUBNETWORKS_ALL_IP_RANGES"
}

# GKE Cluster
resource "google_container_cluster" "primary" {
  name     = "${var.project_name}-${var.environment}"
  location = var.region

  # Regional cluster with 1 node per zone initially
  initial_node_count       = 1
  remove_default_node_pool = true

  network    = google_compute_network.vpc.name
  subnetwork = google_compute_subnetwork.subnet.name

  # IP allocation for pods and services
  ip_allocation_policy {
    cluster_secondary_range_name  = "pods"
    services_secondary_range_name = "services"
  }

  # Workload Identity
  workload_identity_config {
    workload_pool = "${var.project_id}.svc.id.goog"
  }

  # Network policy
  network_policy {
    enabled = true
  }

  # Enable addons
  addons_config {
    http_load_balancing {
      disabled = false
    }
    horizontal_pod_autoscaling {
      disabled = false
    }
    network_policy_config {
      disabled = false
    }
  }

  # Release channel
  release_channel {
    channel = var.release_channel
  }

  # Logging and monitoring
  logging_config {
    enable_components = ["SYSTEM_COMPONENTS", "WORKLOADS"]
  }

  monitoring_config {
    enable_components = ["SYSTEM_COMPONENTS"]
    managed_prometheus {
      enabled = true
    }
  }

  # Master auth settings
  master_auth {
    client_certificate_config {
      issue_client_certificate = false
    }
  }

  # Private cluster config
  private_cluster_config {
    enable_private_nodes    = true
    enable_private_endpoint = false
    master_ipv4_cidr_block  = "172.16.0.0/28"
  }
}

# General purpose node pool
resource "google_container_node_pool" "general" {
  name       = "general-${var.environment}"
  location   = var.region
  cluster    = google_container_cluster.primary.name
  node_count = var.general_node_count_per_zone

  autoscaling {
    min_node_count = var.general_node_min_count
    max_node_count = var.general_node_max_count
  }

  management {
    auto_repair  = true
    auto_upgrade = true
  }

  node_config {
    machine_type = var.general_machine_type
    disk_size_gb = 50
    disk_type    = "pd-standard"

    oauth_scopes = [
      "https://www.googleapis.com/auth/cloud-platform"
    ]

    labels = {
      role        = "general"
      environment = var.environment
    }

    metadata = {
      disable-legacy-endpoints = "true"
    }

    workload_metadata_config {
      mode = "GKE_METADATA"
    }

    shielded_instance_config {
      enable_secure_boot          = true
      enable_integrity_monitoring = true
    }
  }
}

# GPU node pool
resource "google_container_node_pool" "gpu" {
  name       = "gpu-${var.environment}"
  location   = var.region
  cluster    = google_container_cluster.primary.name
  node_count = var.gpu_node_count_per_zone

  autoscaling {
    min_node_count = var.gpu_node_min_count
    max_node_count = var.gpu_node_max_count
  }

  management {
    auto_repair  = true
    auto_upgrade = true
  }

  node_config {
    machine_type = var.gpu_machine_type
    disk_size_gb = 100
    disk_type    = "pd-ssd"

    guest_accelerator {
      type  = var.gpu_type
      count = var.gpu_count_per_node
    }

    oauth_scopes = [
      "https://www.googleapis.com/auth/cloud-platform"
    ]

    labels = {
      role        = "gpu"
      environment = var.environment
      workload    = "comfyui"
    }

    metadata = {
      disable-legacy-endpoints = "true"
    }

    workload_metadata_config {
      mode = "GKE_METADATA"
    }

    taints = [{
      key    = "nvidia.com/gpu"
      value  = "true"
      effect = "NO_SCHEDULE"
    }]

    shielded_instance_config {
      enable_secure_boot          = true
      enable_integrity_monitoring = true
    }
  }
}

# Cloud Storage bucket for models
resource "google_storage_bucket" "models" {
  name          = "${var.project_name}-models-${var.environment}-${var.region}"
  location      = var.region
  storage_class = "STANDARD"

  uniform_bucket_level_access = true

  versioning {
    enabled = true
  }

  encryption {
    default_kms_key_name = var.enable_cmek ? google_kms_crypto_key.storage[0].id : null
  }

  lifecycle_rule {
    condition {
      age = 90
    }
    action {
      type          = "SetStorageClass"
      storage_class = "NEARLINE"
    }
  }
}

# Cloud Storage bucket for outputs
resource "google_storage_bucket" "outputs" {
  name          = "${var.project_name}-outputs-${var.environment}-${var.region}"
  location      = var.region
  storage_class = "STANDARD"

  uniform_bucket_level_access = true

  versioning {
    enabled = true
  }

  lifecycle_rule {
    condition {
      age = 90
    }
    action {
      type = "Delete"
    }
  }

  lifecycle_rule {
    condition {
      age = 30
    }
    action {
      type          = "SetStorageClass"
      storage_class = "NEARLINE"
    }
  }
}

# Service Account for Workload Identity
resource "google_service_account" "comfyui" {
  account_id   = "${var.project_name}-${var.environment}"
  display_name = "ComfyUI 3D Pack Service Account"
  description  = "Service account for ComfyUI workloads"
}

# Grant Storage permissions
resource "google_storage_bucket_iam_member" "models" {
  bucket = google_storage_bucket.models.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.comfyui.email}"
}

resource "google_storage_bucket_iam_member" "outputs" {
  bucket = google_storage_bucket.outputs.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.comfyui.email}"
}

# Workload Identity binding
resource "google_service_account_iam_member" "workload_identity" {
  service_account_id = google_service_account.comfyui.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "serviceAccount:${var.project_id}.svc.id.goog[production/comfyui-3d-pack]"
}

# Cloud SQL (PostgreSQL) - Optional
resource "google_sql_database_instance" "main" {
  count = var.enable_cloud_sql ? 1 : 0

  name             = "${var.project_name}-db-${var.environment}"
  database_version = "POSTGRES_15"
  region           = var.region

  settings {
    tier              = var.db_tier
    availability_type = var.environment == "prod" ? "REGIONAL" : "ZONAL"
    disk_size         = var.db_disk_size
    disk_type         = "PD_SSD"

    backup_configuration {
      enabled    = true
      start_time = "03:00"
    }

    ip_configuration {
      ipv4_enabled    = false
      private_network = google_compute_network.vpc.id
    }

    database_flags {
      name  = "max_connections"
      value = "100"
    }
  }

  deletion_protection = var.environment == "prod" ? true : false
}

resource "google_sql_database" "database" {
  count = var.enable_cloud_sql ? 1 : 0

  name     = "comfyui"
  instance = google_sql_database_instance.main[0].name
}

# Memorystore (Redis) - Optional
resource "google_redis_instance" "cache" {
  count = var.enable_memorystore ? 1 : 0

  name           = "${var.project_name}-redis-${var.environment}"
  tier           = var.redis_tier
  memory_size_gb = var.redis_memory_gb
  region         = var.region

  authorized_network = google_compute_network.vpc.id
  connect_mode       = "PRIVATE_SERVICE_ACCESS"

  redis_version = "REDIS_7_0"

  persistence_config {
    persistence_mode = "RDB"
  }
}

# KMS for encryption (optional)
resource "google_kms_key_ring" "comfyui" {
  count = var.enable_cmek ? 1 : 0

  name     = "${var.project_name}-${var.environment}"
  location = var.region
}

resource "google_kms_crypto_key" "storage" {
  count = var.enable_cmek ? 1 : 0

  name     = "storage-key"
  key_ring = google_kms_key_ring.comfyui[0].id

  lifecycle {
    prevent_destroy = true
  }
}

# Container Registry (Artifact Registry)
resource "google_artifact_registry_repository" "comfyui" {
  location      = var.region
  repository_id = "${var.project_name}-${var.environment}"
  description   = "Docker repository for ComfyUI 3D Pack"
  format        = "DOCKER"
}
