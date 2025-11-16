# Terraform Configuration for AWS Deployment
# Creates EKS cluster, VPC, S3 buckets, and related infrastructure

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.23"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.11"
    }
  }

  backend "s3" {
    bucket         = "comfyui-terraform-state"
    key            = "aws/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "terraform-state-lock"
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "ComfyUI-3D-Pack"
      Environment = var.environment
      ManagedBy   = "Terraform"
      Region      = var.aws_region
    }
  }
}

# Data sources
data "aws_availability_zones" "available" {
  state = "available"
}

data "aws_caller_identity" "current" {}

# VPC Module
module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 5.0"

  name = "${var.project_name}-vpc-${var.environment}"
  cidr = var.vpc_cidr

  azs             = slice(data.aws_availability_zones.available.names, 0, 3)
  private_subnets = var.private_subnet_cidrs
  public_subnets  = var.public_subnet_cidrs

  enable_nat_gateway   = true
  single_nat_gateway   = var.environment == "dev" ? true : false
  enable_dns_hostnames = true
  enable_dns_support   = true

  # Kubernetes tags
  public_subnet_tags = {
    "kubernetes.io/role/elb"                                        = "1"
    "kubernetes.io/cluster/${var.project_name}-${var.environment}" = "shared"
  }

  private_subnet_tags = {
    "kubernetes.io/role/internal-elb"                               = "1"
    "kubernetes.io/cluster/${var.project_name}-${var.environment}" = "shared"
  }

  tags = {
    Name = "${var.project_name}-vpc-${var.environment}"
  }
}

# EKS Cluster
module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "~> 19.0"

  cluster_name    = "${var.project_name}-${var.environment}"
  cluster_version = var.kubernetes_version

  vpc_id     = module.vpc.vpc_id
  subnet_ids = module.vpc.private_subnets

  # Cluster access
  cluster_endpoint_public_access  = true
  cluster_endpoint_private_access = true

  cluster_addons = {
    coredns = {
      most_recent = true
    }
    kube-proxy = {
      most_recent = true
    }
    vpc-cni = {
      most_recent = true
    }
    aws-ebs-csi-driver = {
      most_recent = true
    }
  }

  # OIDC provider for IRSA
  enable_irsa = true

  # Managed node groups
  eks_managed_node_groups = {
    # General purpose nodes
    general = {
      name           = "general-${var.environment}"
      instance_types = var.general_node_instance_types
      capacity_type  = "ON_DEMAND"

      min_size     = var.general_node_min_size
      max_size     = var.general_node_max_size
      desired_size = var.general_node_desired_size

      disk_size = 50

      labels = {
        role = "general"
      }

      tags = {
        "k8s.io/cluster-autoscaler/enabled"                         = "true"
        "k8s.io/cluster-autoscaler/${var.project_name}-${var.environment}" = "owned"
      }
    }

    # GPU nodes for ComfyUI workloads
    gpu = {
      name           = "gpu-${var.environment}"
      instance_types = var.gpu_node_instance_types
      capacity_type  = var.gpu_node_capacity_type # ON_DEMAND or SPOT

      min_size     = var.gpu_node_min_size
      max_size     = var.gpu_node_max_size
      desired_size = var.gpu_node_desired_size

      disk_size = 100

      # GPU-specific settings
      ami_type = "AL2_x86_64_GPU"

      labels = {
        role                = "gpu"
        "nvidia.com/gpu"    = "true"
        "workload"          = "comfyui"
      }

      taints = [{
        key    = "nvidia.com/gpu"
        value  = "true"
        effect = "NO_SCHEDULE"
      }]

      tags = {
        "k8s.io/cluster-autoscaler/enabled"                         = "true"
        "k8s.io/cluster-autoscaler/${var.project_name}-${var.environment}" = "owned"
        "k8s.io/cluster-autoscaler/node-template/label/role"       = "gpu"
      }
    }
  }

  # Cluster security group rules
  cluster_security_group_additional_rules = {
    egress_all = {
      description = "Cluster all egress"
      protocol    = "-1"
      from_port   = 0
      to_port     = 0
      type        = "egress"
      cidr_blocks = ["0.0.0.0/0"]
    }
  }

  # Node security group rules
  node_security_group_additional_rules = {
    ingress_self_all = {
      description = "Node to node all traffic"
      protocol    = "-1"
      from_port   = 0
      to_port     = 0
      type        = "ingress"
      self        = true
    }
    egress_all = {
      description = "Node all egress"
      protocol    = "-1"
      from_port   = 0
      to_port     = 0
      type        = "egress"
      cidr_blocks = ["0.0.0.0/0"]
    }
  }

  tags = {
    Environment = var.environment
  }
}

# S3 Bucket for Models
resource "aws_s3_bucket" "models" {
  bucket = "${var.project_name}-models-${var.environment}-${var.aws_region}"

  tags = {
    Name        = "${var.project_name}-models"
    Purpose     = "model-storage"
    Environment = var.environment
  }
}

resource "aws_s3_bucket_versioning" "models" {
  bucket = aws_s3_bucket.models.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "models" {
  bucket = aws_s3_bucket.models.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "models" {
  bucket = aws_s3_bucket.models.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# S3 Bucket for Outputs
resource "aws_s3_bucket" "outputs" {
  bucket = "${var.project_name}-outputs-${var.environment}-${var.aws_region}"

  tags = {
    Name        = "${var.project_name}-outputs"
    Purpose     = "output-storage"
    Environment = var.environment
  }
}

resource "aws_s3_bucket_versioning" "outputs" {
  bucket = aws_s3_bucket.outputs.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "outputs" {
  bucket = aws_s3_bucket.outputs.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Lifecycle policy for outputs (delete after 90 days)
resource "aws_s3_bucket_lifecycle_configuration" "outputs" {
  bucket = aws_s3_bucket.outputs.id

  rule {
    id     = "delete-old-outputs"
    status = "Enabled"

    expiration {
      days = 90
    }

    noncurrent_version_expiration {
      noncurrent_days = 30
    }
  }
}

# IAM Role for Service Account (IRSA)
resource "aws_iam_role" "comfyui_sa" {
  name = "${var.project_name}-sa-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        Federated = module.eks.oidc_provider_arn
      }
      Action = "sts:AssumeRoleWithWebIdentity"
      Condition = {
        StringEquals = {
          "${module.eks.oidc_provider}:sub" = "system:serviceaccount:production:comfyui-3d-pack"
          "${module.eks.oidc_provider}:aud" = "sts.amazonaws.com"
        }
      }
    }]
  })

  tags = {
    Name = "${var.project_name}-service-account"
  }
}

# IAM Policy for S3 Access
resource "aws_iam_policy" "comfyui_s3" {
  name        = "${var.project_name}-s3-access-${var.environment}"
  description = "Allow ComfyUI to access S3 buckets"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.models.arn,
          "${aws_s3_bucket.models.arn}/*",
          aws_s3_bucket.outputs.arn,
          "${aws_s3_bucket.outputs.arn}/*"
        ]
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "comfyui_s3" {
  role       = aws_iam_role.comfyui_sa.name
  policy_arn = aws_iam_policy.comfyui_s3.arn
}

# RDS PostgreSQL for metadata
module "rds" {
  source  = "terraform-aws-modules/rds/aws"
  version = "~> 6.0"

  count = var.enable_rds ? 1 : 0

  identifier = "${var.project_name}-db-${var.environment}"

  engine               = "postgres"
  engine_version       = "15.4"
  family               = "postgres15"
  major_engine_version = "15"
  instance_class       = var.db_instance_class

  allocated_storage     = var.db_allocated_storage
  max_allocated_storage = var.db_max_allocated_storage

  db_name  = "comfyui"
  username = "comfyui_admin"
  port     = 5432

  multi_az               = var.environment == "prod" ? true : false
  db_subnet_group_name   = module.vpc.database_subnet_group_name
  vpc_security_group_ids = [aws_security_group.rds[0].id]

  maintenance_window      = "Mon:00:00-Mon:03:00"
  backup_window           = "03:00-06:00"
  backup_retention_period = var.environment == "prod" ? 30 : 7

  enabled_cloudwatch_logs_exports = ["postgresql", "upgrade"]

  deletion_protection = var.environment == "prod" ? true : false
  skip_final_snapshot = var.environment != "prod"

  tags = {
    Name = "${var.project_name}-database"
  }
}

resource "aws_security_group" "rds" {
  count = var.enable_rds ? 1 : 0

  name_prefix = "${var.project_name}-rds-"
  vpc_id      = module.vpc.vpc_id

  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [module.eks.node_security_group_id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-rds-sg"
  }
}

# ElastiCache Redis for caching
module "redis" {
  source  = "terraform-aws-modules/elasticache/aws"
  version = "~> 1.0"

  count = var.enable_redis ? 1 : 0

  cluster_id               = "${var.project_name}-redis-${var.environment}"
  engine                   = "redis"
  engine_version           = "7.0"
  node_type                = var.redis_node_type
  num_cache_nodes          = var.redis_num_nodes
  parameter_group_name     = "default.redis7"
  port                     = 6379
  subnet_group_name        = module.vpc.elasticache_subnet_group_name
  security_group_ids       = [aws_security_group.redis[0].id]
  snapshot_retention_limit = var.environment == "prod" ? 5 : 0

  tags = {
    Name = "${var.project_name}-redis"
  }
}

resource "aws_security_group" "redis" {
  count = var.enable_redis ? 1 : 0

  name_prefix = "${var.project_name}-redis-"
  vpc_id      = module.vpc.vpc_id

  ingress {
    from_port       = 6379
    to_port         = 6379
    protocol        = "tcp"
    security_groups = [module.eks.node_security_group_id]
  }

  tags = {
    Name = "${var.project_name}-redis-sg"
  }
}

# CloudWatch Log Group
resource "aws_cloudwatch_log_group" "comfyui" {
  name              = "/aws/eks/${var.project_name}-${var.environment}"
  retention_in_days = var.log_retention_days

  tags = {
    Name = "${var.project_name}-logs"
  }
}

# ECR Repository
resource "aws_ecr_repository" "comfyui" {
  name                 = "${var.project_name}-${var.environment}"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  encryption_configuration {
    encryption_type = "AES256"
  }

  tags = {
    Name = "${var.project_name}-ecr"
  }
}

# ECR Lifecycle Policy
resource "aws_ecr_lifecycle_policy" "comfyui" {
  repository = aws_ecr_repository.comfyui.name

  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "Keep last 10 images"
      selection = {
        tagStatus     = "tagged"
        tagPrefixList = ["v"]
        countType     = "imageCountMoreThan"
        countNumber   = 10
      }
      action = {
        type = "expire"
      }
    }]
  })
}
