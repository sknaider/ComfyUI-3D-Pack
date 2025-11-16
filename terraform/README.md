# Infrastructure as Code with Terraform

This directory contains Terraform configurations for deploying ComfyUI-3D-Pack infrastructure across multiple cloud providers.

## Overview

```
terraform/
├── aws/           # AWS EKS deployment
│   ├── main.tf
│   ├── variables.tf
│   ├── outputs.tf
│   └── README.md
├── gcp/           # GCP GKE deployment
│   ├── main.tf
│   ├── variables.tf
│   ├── outputs.tf
│   └── README.md
└── README.md      # This file
```

## Supported Cloud Providers

| Provider | Kubernetes | Object Storage | Database       | Cache         | Status |
|----------|------------|----------------|----------------|---------------|--------|
| AWS      | EKS        | S3             | RDS PostgreSQL | ElastiCache   | ✅     |
| GCP      | GKE        | Cloud Storage  | Cloud SQL      | Memorystore   | ✅     |
| Azure    | AKS        | Blob Storage   | Azure Database | Azure Cache   | 🚧     |

## Quick Start

### AWS Deployment

```bash
cd terraform/aws

# Initialize
terraform init

# Create terraform.tfvars with your settings
cat > terraform.tfvars <<EOF
aws_region   = "us-east-1"
project_name = "comfyui-3d-pack"
environment  = "prod"
EOF

# Plan and apply
terraform plan -out=tfplan
terraform apply tfplan

# Configure kubectl
$(terraform output -raw configure_kubectl)

# Deploy with Helm
cd ../../
helm install comfyui helm/comfyui-3d-pack \
  -f helm/comfyui-3d-pack/values-us-east-1.yaml \
  --namespace production \
  --create-namespace
```

### GCP Deployment

```bash
cd terraform/gcp

# Initialize
terraform init

# Create terraform.tfvars
cat > terraform.tfvars <<EOF
project_id   = "my-gcp-project"
region       = "us-central1"
project_name = "comfyui-3d-pack"
environment  = "prod"
EOF

# Plan and apply
terraform plan -out=tfplan
terraform apply tfplan

# Configure kubectl
$(terraform output -raw configure_kubectl)

# Deploy with Helm
cd ../../
helm install comfyui helm/comfyui-3d-pack \
  --namespace production \
  --create-namespace
```

## Features

### Common Features (All Providers)

- **Kubernetes Cluster** - Managed Kubernetes service
- **GPU Node Pools** - Dedicated GPU nodes for workloads
- **Object Storage** - Cloud-native object storage
- **Database** - Managed PostgreSQL database (optional)
- **Caching** - Managed Redis cache (optional)
- **Container Registry** - Private container registry
- **Networking** - VPC, subnets, NAT gateways
- **Security** - IAM roles, encryption at rest
- **Monitoring** - Cloud-native monitoring integration

### AWS-Specific Features

- **IRSA** - IAM Roles for Service Accounts
- **EBS CSI Driver** - For persistent volumes
- **AWS Load Balancer Controller** - For ingress
- **S3 Cross-Region Replication** - For multi-region
- **VPC Endpoints** - For private AWS service access

### GCP-Specific Features

- **Workload Identity** - GCP equivalent of IRSA
- **GKE Autopilot** - Optional fully-managed mode
- **Cloud Armor** - DDoS protection
- **Binary Authorization** - Container image signing
- **VPC-native networking** - For better performance

## Architecture Comparison

### AWS Architecture

```
┌─────────────────────────────────────┐
│           AWS Account                │
├─────────────────────────────────────┤
│  VPC (10.0.0.0/16)                  │
│  ├─ Public Subnets (3 AZs)          │
│  ├─ Private Subnets (3 AZs)         │
│  │  └─ EKS Cluster                  │
│  │     ├─ General Nodes (t3.large)  │
│  │     └─ GPU Nodes (g4dn.xlarge)   │
│  └─ Database Subnets                │
│     ├─ RDS PostgreSQL               │
│     └─ ElastiCache Redis            │
│                                      │
│  S3 Buckets (encrypted, versioned)  │
│  ECR Repository                      │
│  CloudWatch Logs                     │
└─────────────────────────────────────┘
```

### GCP Architecture

```
┌─────────────────────────────────────┐
│           GCP Project                │
├─────────────────────────────────────┤
│  VPC Network                         │
│  └─ Regional Subnet                  │
│     └─ GKE Cluster (Regional)       │
│        ├─ General Pool (n1-std-4)   │
│        └─ GPU Pool (n1-std-4+T4)    │
│                                      │
│  Cloud SQL PostgreSQL (Private IP)  │
│  Memorystore Redis                   │
│                                      │
│  Cloud Storage Buckets               │
│  Artifact Registry                   │
│  Cloud Logging                       │
└─────────────────────────────────────┘
```

## Cost Optimization

### Development Environment

Reduce costs for dev/test:

```hcl
# AWS
environment                = "dev"
gpu_node_capacity_type     = "SPOT"        # 70% cheaper
gpu_node_desired_size      = 1             # Minimal GPU nodes
general_node_desired_size  = 2             # Minimal general nodes
enable_rds                 = false         # Use in-cluster PostgreSQL
enable_redis               = false         # Use in-cluster Redis

# GCP
environment                = "dev"
gpu_node_count_per_zone    = 0             # Start with 0 GPU nodes
general_node_count_per_zone = 1            # Minimal general nodes
enable_cloud_sql           = false
enable_memorystore         = false
```

### Production Environment

Optimized for reliability:

```hcl
# AWS
environment                = "prod"
gpu_node_capacity_type     = "ON_DEMAND"   # More reliable
gpu_node_min_size          = 3             # Always available
enable_rds                 = true          # Managed database
db_instance_class          = "db.r5.large" # Production-ready

# GCP
environment                = "prod"
gpu_node_min_count         = 2
redis_tier                 = "STANDARD_HA" # High availability
db_tier                    = "db-custom-4-16384"
```

### Estimated Monthly Costs

| Configuration      | AWS (us-east-1) | GCP (us-central1) |
|--------------------|-----------------|-------------------|
| **Development**    | ~$400/month     | ~$350/month       |
| 1 GPU node (SPOT)  | $150            | $180              |
| 2 General nodes    | $150            | $120              |
| Storage & Network  | $100            | $50               |
|                    |                 |                   |
| **Production**     | ~$1,600/month   | ~$1,800/month     |
| 3 GPU nodes        | $1,100          | $1,200            |
| 3 General nodes    | $225            | $180              |
| RDS/Cloud SQL      | $150            | $200              |
| Redis/Memorystore  | $75             | $150              |
| Storage & Network  | $50             | $70               |

## Multi-Cloud Deployment

Deploy to multiple providers for redundancy:

```bash
# Deploy to AWS (Primary)
cd terraform/aws
terraform apply -var="environment=prod"

# Deploy to GCP (Backup)
cd ../gcp
terraform apply -var="environment=prod"

# Configure global load balancing
# - AWS Route 53 with geolocation routing
# - GCP Cloud DNS with geo-routing
# - Cloudflare Load Balancer
```

## State Management

### AWS (S3 Backend)

Create state bucket before first use:

```bash
aws s3 mb s3://comfyui-terraform-state --region us-east-1
aws s3api put-bucket-versioning \
  --bucket comfyui-terraform-state \
  --versioning-configuration Status=Enabled

aws dynamodb create-table \
  --table-name terraform-state-lock \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --region us-east-1
```

### GCP (GCS Backend)

Create state bucket:

```bash
gsutil mb gs://comfyui-terraform-state
gsutil versioning set on gs://comfyui-terraform-state
```

## Best Practices

### 1. Use Workspaces for Multiple Environments

```bash
# Create workspaces
terraform workspace new dev
terraform workspace new staging
terraform workspace new prod

# Switch between environments
terraform workspace select prod
terraform plan -var="environment=prod"
```

### 2. Remote State Locking

Always use remote backends with locking:
- AWS: S3 + DynamoDB
- GCP: GCS (has built-in locking)
- Azure: Azure Storage (has built-in locking)

### 3. Tagging Strategy

Consistent tagging across all resources:

```hcl
default_tags = {
  Project     = "ComfyUI-3D-Pack"
  Environment = var.environment
  ManagedBy   = "Terraform"
  Team        = "ML-Engineering"
  CostCenter  = "R&D"
}
```

### 4. Security

- **Encryption**: Enable encryption at rest for all storage
- **Private clusters**: Use private IP addresses for nodes
- **Least privilege**: Minimal IAM permissions
- **Secrets management**: Use cloud provider secrets managers
- **Network policies**: Restrict pod-to-pod communication

### 5. CI/CD Integration

Use Terraform in CI/CD pipelines:

```yaml
# .github/workflows/terraform.yml
name: Terraform
on: [push]
jobs:
  terraform:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: hashicorp/setup-terraform@v2
      - run: terraform init
      - run: terraform plan
      - run: terraform apply -auto-approve  # Only on main branch
```

## Troubleshooting

### Common Issues

#### 1. Quota Limits

**Problem**: "Quota exceeded for resource 'GPUS_ALL_REGIONS'"

**Solution**:
- Request quota increase in cloud provider console
- Use different instance types
- Deploy across multiple regions

#### 2. State Lock

**Problem**: "Error acquiring the state lock"

**Solution**:
```bash
# Force unlock (use with caution!)
terraform force-unlock LOCK_ID
```

#### 3. Resource Already Exists

**Problem**: "Resource already exists"

**Solution**:
```bash
# Import existing resource
terraform import aws_s3_bucket.models bucket-name

# Or destroy and recreate
terraform destroy -target=aws_s3_bucket.models
terraform apply
```

## Migrating Between Providers

To migrate from one cloud to another:

1. **Export data** from source cloud
2. **Deploy infrastructure** on target cloud
3. **Import data** to target cloud
4. **Update DNS** to point to new infrastructure
5. **Verify** application functionality
6. **Decommission** old infrastructure

See `docs/MULTI_REGION_DEPLOYMENT.md` for detailed migration guide.

## Additional Resources

### Documentation
- [Terraform AWS Provider](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)
- [Terraform GCP Provider](https://registry.terraform.io/providers/hashicorp/google/latest/docs)
- [Terraform Best Practices](https://www.terraform-best-practices.com/)

### Tools
- [tflint](https://github.com/terraform-linters/tflint) - Terraform linter
- [terrascan](https://github.com/tenable/terrascan) - Security scanner
- [infracost](https://www.infracost.io/) - Cost estimation

### Examples
- See individual provider READMEs for detailed examples
- Check `examples/` directory for sample configurations

## Contributing

When adding new cloud providers:

1. Create new directory under `terraform/`
2. Follow existing naming conventions
3. Include main.tf, variables.tf, outputs.tf
4. Add comprehensive README.md
5. Test in dev environment first
6. Update this main README

## Support

For infrastructure issues:
- Check provider-specific README
- Review Terraform documentation
- Open GitHub issue with `infrastructure` label
