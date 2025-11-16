# AWS Infrastructure with Terraform

This Terraform configuration deploys ComfyUI-3D-Pack infrastructure on AWS including EKS, S3, RDS, and ElastiCache.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        AWS Account                           │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌────────────────VPC (10.0.0.0/16)──────────────────┐     │
│  │                                                     │     │
│  │  ┌──────────────┐  ┌──────────────┐  ┌─────────┐ │     │
│  │  │ Public       │  │ Private      │  │ Database│ │     │
│  │  │ Subnets      │  │ Subnets      │  │ Subnets │ │     │
│  │  │ (3 AZs)      │  │ (3 AZs)      │  │ (3 AZs) │ │     │
│  │  └──────────────┘  └──────────────┘  └─────────┘ │     │
│  │         │                 │                │       │     │
│  │    ┌────▼─────┐      ┌───▼───┐       ┌───▼──┐   │     │
│  │    │ NAT GW   │      │  EKS  │       │ RDS  │   │     │
│  │    │   (3x)   │      │Cluster│       │  DB  │   │     │
│  │    └──────────┘      └───┬───┘       └──────┘   │     │
│  │                          │                        │     │
│  │                  ┌───────▼────────┐              │     │
│  │                  │  Node Groups   │              │     │
│  │                  │ • General (t3) │              │     │
│  │                  │ • GPU (g4dn)   │              │     │
│  │                  └────────────────┘              │     │
│  └──────────────────────────────────────────────────┘     │
│                                                             │
│  ┌────────────────────────────────────────────┐           │
│  │  S3 Buckets                                 │           │
│  │  • Models (versioned, encrypted)            │           │
│  │  • Outputs (lifecycle policy)               │           │
│  └────────────────────────────────────────────┘           │
│                                                             │
│  ┌────────────────────────────────────────────┐           │
│  │  ElastiCache Redis                          │           │
│  │  • Multi-node cluster                       │           │
│  │  • Encryption at rest & transit             │           │
│  └────────────────────────────────────────────┘           │
│                                                             │
│  ┌────────────────────────────────────────────┐           │
│  │  ECR (Container Registry)                   │           │
│  │  • Image scanning enabled                   │           │
│  │  • Lifecycle policies                       │           │
│  └────────────────────────────────────────────┘           │
└─────────────────────────────────────────────────────────────┘
```

## Prerequisites

1. **AWS CLI** configured with appropriate credentials:
   ```bash
   aws configure
   ```

2. **Terraform** >= 1.5.0:
   ```bash
   terraform version
   ```

3. **AWS IAM Permissions**: Your AWS user/role needs permissions for:
   - VPC, Subnets, Route Tables, NAT Gateways
   - EKS Clusters and Node Groups
   - EC2 (for nodes)
   - S3 Buckets
   - RDS (if enabled)
   - ElastiCache (if enabled)
   - IAM Roles and Policies
   - CloudWatch Logs
   - ECR

## Quick Start

### 1. Initialize Terraform

```bash
cd terraform/aws
terraform init
```

### 2. Create terraform.tfvars

```hcl
# terraform.tfvars
aws_region   = "us-east-1"
project_name = "comfyui-3d-pack"
environment  = "prod"

# VPC Configuration
vpc_cidr             = "10.0.0.0/16"
private_subnet_cidrs = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
public_subnet_cidrs  = ["10.0.101.0/24", "10.0.102.0/24", "10.0.103.0/24"]

# EKS Configuration
kubernetes_version = "1.28"

# General Nodes
general_node_instance_types = ["t3.large"]
general_node_min_size      = 2
general_node_max_size      = 10
general_node_desired_size  = 3

# GPU Nodes
gpu_node_instance_types = ["g4dn.xlarge"]
gpu_node_capacity_type  = "ON_DEMAND"  # or "SPOT" for cost savings
gpu_node_min_size      = 2
gpu_node_max_size      = 10
gpu_node_desired_size  = 3

# Database
enable_rds            = true
db_instance_class     = "db.t3.medium"
db_allocated_storage  = 50

# Cache
enable_redis     = true
redis_node_type  = "cache.t3.medium"
redis_num_nodes  = 2

# Logging
log_retention_days = 30
```

### 3. Plan Deployment

```bash
terraform plan -out=tfplan
```

Review the plan to ensure it matches your expectations.

### 4. Apply Configuration

```bash
terraform apply tfplan
```

This will create:
- VPC with public, private, and database subnets
- EKS cluster with general and GPU node groups
- S3 buckets for models and outputs
- RDS PostgreSQL database (if enabled)
- ElastiCache Redis cluster (if enabled)
- ECR repository
- IAM roles and policies
- CloudWatch log groups

### 5. Configure kubectl

```bash
aws eks update-kubeconfig --region us-east-1 --name comfyui-3d-pack-prod
```

### 6. Verify Cluster

```bash
kubectl get nodes
kubectl get pods --all-namespaces
```

## Deploying ComfyUI with Helm

After infrastructure is created:

```bash
# Get outputs
terraform output -json > ../outputs.json

# Extract service account role ARN
SA_ROLE=$(terraform output -raw service_account_role_arn)

# Deploy with Helm
helm install comfyui ../../helm/comfyui-3d-pack \
  -f ../../helm/comfyui-3d-pack/values-us-east-1.yaml \
  --set serviceAccount.annotations."eks\.amazonaws\.com/role-arn"=$SA_ROLE \
  --namespace production \
  --create-namespace
```

## Configuration Options

### GPU Node Types

Choose based on your workload:

| Instance Type | vCPUs | RAM   | GPUs | GPU Memory | Use Case                    |
|---------------|-------|-------|------|------------|-----------------------------|
| g4dn.xlarge   | 4     | 16GB  | 1    | 16GB       | Development, small models   |
| g4dn.2xlarge  | 8     | 32GB  | 1    | 16GB       | Medium workloads            |
| g4dn.4xlarge  | 16    | 64GB  | 1    | 16GB       | Large models                |
| g5.xlarge     | 4     | 16GB  | 1    | 24GB       | Latest GPU, better price    |
| g5.2xlarge    | 8     | 32GB  | 1    | 24GB       | Production workloads        |

### Cost Optimization

1. **Use SPOT instances for GPU nodes** (up to 70% cheaper):
   ```hcl
   gpu_node_capacity_type = "SPOT"
   ```

2. **Enable cluster autoscaler** - nodes scale based on demand

3. **Use lifecycle policies** - S3 automatically archives old outputs

4. **Right-size databases**:
   - Dev: `db.t3.micro`, `cache.t3.micro`
   - Prod: `db.r5.large`, `cache.r5.large`

### Multi-Region Setup

To deploy to multiple regions:

```bash
# Deploy to us-east-1
terraform apply -var="aws_region=us-east-1" -var="environment=prod"

# Deploy to eu-west-1
terraform apply -var="aws_region=eu-west-1" -var="environment=prod"

# Deploy to ap-southeast-1
terraform apply -var="aws_region=ap-southeast-1" -var="environment=prod"
```

## Outputs

After `terraform apply`, use these commands to get important values:

```bash
# Cluster endpoint
terraform output cluster_endpoint

# Configure kubectl command
terraform output -raw configure_kubectl | bash

# S3 bucket names
terraform output models_bucket_id
terraform output outputs_bucket_id

# Service account role (for Helm)
terraform output service_account_role_arn

# Database endpoint
terraform output db_instance_endpoint

# Redis endpoint
terraform output redis_endpoint

# All Helm values
terraform output -json helm_values
```

## State Management

This configuration uses S3 backend for state storage. Before first use:

```bash
# Create state bucket
aws s3 mb s3://comfyui-terraform-state --region us-east-1

# Enable versioning
aws s3api put-bucket-versioning \
  --bucket comfyui-terraform-state \
  --versioning-configuration Status=Enabled

# Create DynamoDB table for locking
aws dynamodb create-table \
  --table-name terraform-state-lock \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --region us-east-1
```

## Updating Infrastructure

```bash
# Pull latest changes
terraform plan

# Apply updates
terraform apply

# Update specific resource
terraform apply -target=module.eks
```

## Destroying Infrastructure

**WARNING:** This will delete all resources including data!

```bash
# Preview destruction
terraform plan -destroy

# Destroy everything
terraform destroy

# Destroy specific resource
terraform destroy -target=aws_s3_bucket.outputs
```

## Troubleshooting

### EKS Cluster Not Accessible

```bash
# Update kubeconfig
aws eks update-kubeconfig --region us-east-1 --name comfyui-3d-pack-prod

# Verify AWS credentials
aws sts get-caller-identity

# Check cluster status
aws eks describe-cluster --name comfyui-3d-pack-prod --region us-east-1
```

### Nodes Not Joining Cluster

```bash
# Check node group status
aws eks describe-nodegroup \
  --cluster-name comfyui-3d-pack-prod \
  --nodegroup-name gpu-prod \
  --region us-east-1

# View node logs
aws ec2 describe-instances \
  --filters "Name=tag:eks:nodegroup-name,Values=gpu-prod" \
  --region us-east-1
```

### GPU Not Available

```bash
# Install NVIDIA device plugin
kubectl apply -f https://raw.githubusercontent.com/NVIDIA/k8s-device-plugin/v0.14.0/nvidia-device-plugin.yml

# Verify GPU nodes
kubectl get nodes -o json | jq '.items[].status.capacity'
```

## Security Best Practices

1. **Enable encryption at rest**:
   - EBS volumes (enabled by default)
   - S3 buckets (enabled)
   - RDS databases (enabled)

2. **Network isolation**:
   - Private subnets for workloads
   - Security groups with minimal access
   - VPC endpoints for AWS services

3. **IAM**:
   - Use IRSA (IAM Roles for Service Accounts)
   - Principle of least privilege
   - Rotate credentials regularly

4. **Monitoring**:
   - CloudWatch logs enabled
   - VPC Flow Logs
   - GuardDuty for threat detection

## Cost Estimation

Estimated monthly costs for production deployment:

| Resource                    | Cost (us-east-1)  |
|-----------------------------|-------------------|
| EKS Cluster                 | $73/month         |
| GPU Nodes (3x g4dn.xlarge)  | ~$1,095/month     |
| General Nodes (3x t3.large) | ~$225/month       |
| RDS (db.t3.medium)          | ~$70/month        |
| ElastiCache (2x t3.medium)  | ~$100/month       |
| S3 Storage (1TB)            | ~$23/month        |
| Data Transfer               | Variable          |
| **Total**                   | **~$1,586/month** |

Costs can be reduced significantly with:
- SPOT instances for GPU nodes (save ~70%)
- Smaller instance types in dev/staging
- Autoscaling to zero during off-hours

## Additional Resources

- [AWS EKS Best Practices](https://aws.github.io/aws-eks-best-practices/)
- [Terraform AWS Modules](https://registry.terraform.io/namespaces/terraform-aws-modules)
- [EKS Node Groups](https://docs.aws.amazon.com/eks/latest/userguide/managed-node-groups.html)
- [GPU Instance Types](https://aws.amazon.com/ec2/instance-types/g4/)

## Support

For issues with:
- Terraform: Check [Terraform AWS Provider docs](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)
- EKS: See [AWS EKS documentation](https://docs.aws.amazon.com/eks/)
- ComfyUI: Check main project README
