# Outputs for AWS Terraform Configuration

# VPC Outputs
output "vpc_id" {
  description = "VPC ID"
  value       = module.vpc.vpc_id
}

output "vpc_cidr" {
  description = "VPC CIDR block"
  value       = module.vpc.vpc_cidr_block
}

output "private_subnet_ids" {
  description = "Private subnet IDs"
  value       = module.vpc.private_subnets
}

output "public_subnet_ids" {
  description = "Public subnet IDs"
  value       = module.vpc.public_subnets
}

# EKS Outputs
output "cluster_id" {
  description = "EKS cluster ID"
  value       = module.eks.cluster_id
}

output "cluster_arn" {
  description = "EKS cluster ARN"
  value       = module.eks.cluster_arn
}

output "cluster_endpoint" {
  description = "EKS cluster endpoint"
  value       = module.eks.cluster_endpoint
}

output "cluster_security_group_id" {
  description = "Security group ID attached to the EKS cluster"
  value       = module.eks.cluster_security_group_id
}

output "cluster_certificate_authority_data" {
  description = "Base64 encoded certificate data required to communicate with the cluster"
  value       = module.eks.cluster_certificate_authority_data
  sensitive   = true
}

output "cluster_oidc_issuer_url" {
  description = "The URL on the EKS cluster OIDC Issuer"
  value       = module.eks.cluster_oidc_issuer_url
}

output "oidc_provider_arn" {
  description = "ARN of the OIDC Provider for EKS"
  value       = module.eks.oidc_provider_arn
}

# Node Group Outputs
output "node_groups" {
  description = "EKS node groups"
  value       = module.eks.eks_managed_node_groups
}

# S3 Outputs
output "models_bucket_id" {
  description = "S3 bucket ID for models"
  value       = aws_s3_bucket.models.id
}

output "models_bucket_arn" {
  description = "S3 bucket ARN for models"
  value       = aws_s3_bucket.models.arn
}

output "outputs_bucket_id" {
  description = "S3 bucket ID for outputs"
  value       = aws_s3_bucket.outputs.id
}

output "outputs_bucket_arn" {
  description = "S3 bucket ARN for outputs"
  value       = aws_s3_bucket.outputs.arn
}

# IAM Outputs
output "service_account_role_arn" {
  description = "ARN of IAM role for service account"
  value       = aws_iam_role.comfyui_sa.arn
}

output "service_account_role_name" {
  description = "Name of IAM role for service account"
  value       = aws_iam_role.comfyui_sa.name
}

# RDS Outputs
output "db_instance_endpoint" {
  description = "RDS instance endpoint"
  value       = var.enable_rds ? module.rds[0].db_instance_endpoint : null
}

output "db_instance_name" {
  description = "RDS instance database name"
  value       = var.enable_rds ? module.rds[0].db_instance_name : null
}

output "db_instance_username" {
  description = "RDS instance master username"
  value       = var.enable_rds ? module.rds[0].db_instance_username : null
  sensitive   = true
}

output "db_instance_port" {
  description = "RDS instance port"
  value       = var.enable_rds ? module.rds[0].db_instance_port : null
}

# Redis Outputs
output "redis_cluster_id" {
  description = "Redis cluster ID"
  value       = var.enable_redis ? module.redis[0].cluster_id : null
}

output "redis_endpoint" {
  description = "Redis primary endpoint"
  value       = var.enable_redis ? module.redis[0].cache_nodes[0].address : null
}

output "redis_port" {
  description = "Redis port"
  value       = var.enable_redis ? module.redis[0].port : null
}

# ECR Outputs
output "ecr_repository_url" {
  description = "ECR repository URL"
  value       = aws_ecr_repository.comfyui.repository_url
}

output "ecr_repository_arn" {
  description = "ECR repository ARN"
  value       = aws_ecr_repository.comfyui.arn
}

# CloudWatch Outputs
output "cloudwatch_log_group_name" {
  description = "CloudWatch log group name"
  value       = aws_cloudwatch_log_group.comfyui.name
}

output "cloudwatch_log_group_arn" {
  description = "CloudWatch log group ARN"
  value       = aws_cloudwatch_log_group.comfyui.arn
}

# Kubernetes Configuration Command
output "configure_kubectl" {
  description = "Command to configure kubectl"
  value       = "aws eks update-kubeconfig --region ${var.aws_region} --name ${module.eks.cluster_name}"
}

# Helm Values Output
output "helm_values" {
  description = "Values to use with Helm deployment"
  value = {
    region                = var.aws_region
    serviceAccountRoleArn = aws_iam_role.comfyui_sa.arn
    objectStorage = {
      enabled  = true
      type     = "s3"
      bucket   = aws_s3_bucket.models.id
      region   = var.aws_region
    }
    redis = var.enable_rds ? {
      enabled  = true
      host     = module.redis[0].cache_nodes[0].address
      port     = module.redis[0].port
    } : null
    postgresql = var.enable_rds ? {
      enabled  = true
      host     = split(":", module.rds[0].db_instance_endpoint)[0]
      port     = module.rds[0].db_instance_port
      database = module.rds[0].db_instance_name
      username = module.rds[0].db_instance_username
    } : null
  }
  sensitive = true
}
