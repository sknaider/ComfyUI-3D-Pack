# Outputs for GCP Terraform Configuration

# Network Outputs
output "network_name" {
  description = "VPC network name"
  value       = google_compute_network.vpc.name
}

output "subnet_name" {
  description = "Subnet name"
  value       = google_compute_subnetwork.subnet.name
}

# GKE Outputs
output "cluster_name" {
  description = "GKE cluster name"
  value       = google_container_cluster.primary.name
}

output "cluster_endpoint" {
  description = "GKE cluster endpoint"
  value       = google_container_cluster.primary.endpoint
  sensitive   = true
}

output "cluster_ca_certificate" {
  description = "GKE cluster CA certificate"
  value       = google_container_cluster.primary.master_auth[0].cluster_ca_certificate
  sensitive   = true
}

output "cluster_location" {
  description = "GKE cluster location"
  value       = google_container_cluster.primary.location
}

# Storage Outputs
output "models_bucket_name" {
  description = "Cloud Storage bucket for models"
  value       = google_storage_bucket.models.name
}

output "models_bucket_url" {
  description = "Cloud Storage bucket URL for models"
  value       = google_storage_bucket.models.url
}

output "outputs_bucket_name" {
  description = "Cloud Storage bucket for outputs"
  value       = google_storage_bucket.outputs.name
}

output "outputs_bucket_url" {
  description = "Cloud Storage bucket URL for outputs"
  value       = google_storage_bucket.outputs.url
}

# Service Account Outputs
output "service_account_email" {
  description = "Service account email"
  value       = google_service_account.comfyui.email
}

# Database Outputs
output "db_instance_name" {
  description = "Cloud SQL instance name"
  value       = var.enable_cloud_sql ? google_sql_database_instance.main[0].name : null
}

output "db_connection_name" {
  description = "Cloud SQL connection name"
  value       = var.enable_cloud_sql ? google_sql_database_instance.main[0].connection_name : null
}

output "db_private_ip" {
  description = "Cloud SQL private IP"
  value       = var.enable_cloud_sql ? google_sql_database_instance.main[0].private_ip_address : null
}

# Redis Outputs
output "redis_host" {
  description = "Memorystore Redis host"
  value       = var.enable_memorystore ? google_redis_instance.cache[0].host : null
}

output "redis_port" {
  description = "Memorystore Redis port"
  value       = var.enable_memorystore ? google_redis_instance.cache[0].port : null
}

# Artifact Registry
output "artifact_registry_url" {
  description = "Artifact Registry repository URL"
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.comfyui.repository_id}"
}

# kubectl Configuration
output "configure_kubectl" {
  description = "Command to configure kubectl"
  value       = "gcloud container clusters get-credentials ${google_container_cluster.primary.name} --region ${var.region} --project ${var.project_id}"
}

# Helm Values
output "helm_values" {
  description = "Values for Helm deployment"
  value = {
    region = var.region
    serviceAccount = {
      annotations = {
        "iam.gke.io/gcp-service-account" = google_service_account.comfyui.email
      }
    }
    objectStorage = {
      enabled = true
      type    = "gcs"
      bucket  = google_storage_bucket.models.name
      region  = var.region
    }
    redis = var.enable_memorystore ? {
      enabled = true
      host    = google_redis_instance.cache[0].host
      port    = google_redis_instance.cache[0].port
    } : null
    postgresql = var.enable_cloud_sql ? {
      enabled        = true
      host           = google_sql_database_instance.main[0].private_ip_address
      port           = 5432
      database       = "comfyui"
      connectionName = google_sql_database_instance.main[0].connection_name
    } : null
  }
  sensitive = true
}
