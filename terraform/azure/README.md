# Azure Infrastructure with Terraform

This Terraform configuration deploys ComfyUI-3D-Pack infrastructure on Azure including AKS, Blob Storage, Database, and Cache.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Azure Subscription                       │
├─────────────────────────────────────────────────────────────┤
│  Resource Group: comfyui-3d-pack-prod-rg                    │
│                                                              │
│  ┌─────────────Virtual Network (10.1.0.0/16)─────────────┐ │
│  │                                                          │ │
│  │  ┌──────────AKS Subnet (10.1.0.0/20)──────────┐        │ │
│  │  │                                              │        │ │
│  │  │  AKS Cluster: comfyui-aks-prod             │        │ │
│  │  │  ├─ System Node Pool (Standard_D4s_v3)     │        │ │
│  │  │  ├─ User Node Pool (Standard_D8s_v3)       │        │ │
│  │  │  └─ GPU Node Pool (Standard_NC6s_v3)       │        │ │
│  │  │                                              │        │ │
│  │  └──────────────────────────────────────────────┘        │ │
│  │                                                          │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                              │
│  Storage Accounts                                            │
│  ├─ Models (GRS, versioned)                                 │
│  └─ Outputs (LRS, versioned, lifecycle)                     │
│                                                              │
│  Azure Database for PostgreSQL (Flexible Server)            │
│  └─ High Availability: Zone Redundant                       │
│                                                              │
│  Azure Cache for Redis (Standard)                           │
│  └─ SSL/TLS Enabled                                         │
│                                                              │
│  Azure Container Registry (Premium)                         │
│  └─ Geo-replication enabled                                 │
│                                                              │
│  Log Analytics Workspace                                     │
│  └─ Application Insights                                    │
└─────────────────────────────────────────────────────────────┘
```

## Prerequisites

1. **Azure CLI** installed and configured:
   ```bash
   az --version
   az login
   az account set --subscription "YOUR_SUBSCRIPTION_ID"
   ```

2. **Terraform** >= 1.5.0:
   ```bash
   terraform version
   ```

3. **Azure Permissions**: Contributor role on subscription or resource group

## Quick Start

### 1. Initialize Terraform

```bash
cd terraform/azure

# Create backend storage (first time only)
az group create --name terraform-state-rg --location eastus
az storage account create \
  --name comfyuiterraformstate \
  --resource-group terraform-state-rg \
  --location eastus \
  --sku Standard_LRS

az storage container create \
  --name tfstate \
  --account-name comfyuiterraformstate

# Initialize
terraform init
```

### 2. Create terraform.tfvars

```hcl
# terraform.tfvars
project_name = "comfyui-3d-pack"
environment  = "prod"
location     = "eastus"

# Network
vnet_address_space         = "10.1.0.0/16"
aks_subnet_address_prefix  = "10.1.0.0/20"

# AKS
kubernetes_version = "1.28"

# Azure AD admin group (get with: az ad group show --group "AKS-Admins")
admin_group_object_ids = ["xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"]

# System nodes
system_node_vm_size = "Standard_D4s_v3"
system_node_count   = 3
system_node_min_count = 2
system_node_max_count = 10

# User nodes
user_node_vm_size = "Standard_D8s_v3"
user_node_count   = 3
user_node_min_count = 2
user_node_max_count = 20

# GPU nodes
gpu_node_vm_size  = "Standard_NC6s_v3"  # 1x V100
gpu_node_count    = 2
gpu_node_min_count = 2
gpu_node_max_count = 10

# Database
enable_postgresql  = true
db_sku_name        = "GP_Standard_D2s_v3"
db_storage_mb      = 51200  # 50GB
db_admin_password  = "YourSecurePassword123!"  # Use Azure Key Vault in production

# Cache
enable_redis   = true
redis_sku_name = "Standard"
redis_capacity = 2

# Logging
log_retention_days = 30
```

### 3. Plan and Apply

```bash
# Plan
terraform plan -out=tfplan

# Apply
terraform apply tfplan
```

### 4. Configure kubectl

```bash
az aks get-credentials \
  --resource-group comfyui-3d-pack-prod-rg \
  --name comfyui-aks-prod

# Verify
kubectl get nodes
```

### 5. Install GPU Operator

```bash
# Add NVIDIA Helm repo
helm repo add nvidia https://helm.ngc.nvidia.com/nvidia
helm repo update

# Install GPU Operator
helm install gpu-operator nvidia/gpu-operator \
  --namespace gpu-operator \
  --create-namespace \
  --wait

# Verify GPUs
kubectl get nodes -L beta.kubernetes.io/instance-type
kubectl describe nodes | grep -A 5 "nvidia.com/gpu"
```

### 6. Deploy ComfyUI

```bash
# Get Helm values from Terraform
terraform output -json helm_values > values-generated.json

# Deploy
helm install comfyui ../../helm/comfyui-3d-pack \
  --namespace production \
  --create-namespace
```

## Azure VM Sizes

### GPU VM Sizes

| VM Size             | vCPUs | RAM    | GPUs           | GPU Memory | Cost/Month* |
|---------------------|-------|--------|----------------|------------|-------------|
| Standard_NC6s_v3    | 6     | 112GB  | 1x V100        | 16GB       | ~$1,800     |
| Standard_NC12s_v3   | 12    | 224GB  | 2x V100        | 32GB       | ~$3,600     |
| Standard_NC24s_v3   | 24    | 448GB  | 4x V100        | 64GB       | ~$7,200     |
| Standard_NC6s_v2    | 6     | 112GB  | 1x P100        | 16GB       | ~$1,200     |
| Standard_NC4as_T4_v3| 4     | 28GB   | 1x T4          | 16GB       | ~$400       |

*Approximate costs for East US region

### General VM Sizes

| VM Size             | vCPUs | RAM    | Use Case            | Cost/Month* |
|---------------------|-------|--------|---------------------|-------------|
| Standard_D2s_v3     | 2     | 8GB    | Dev/test            | ~$100       |
| Standard_D4s_v3     | 4     | 16GB   | System nodes        | ~$200       |
| Standard_D8s_v3     | 8     | 32GB   | User nodes          | ~$400       |
| Standard_D16s_v3    | 16    | 64GB   | Large workloads     | ~$800       |

## Configuration Options

### High Availability

For production, enable zone redundancy:

```hcl
# In main.tf, uncomment:
default_node_pool {
  zones = ["1", "2", "3"]  # Availability zones
}

high_availability {
  mode = "ZoneRedundant"
}
```

### Cost Optimization

For development:

```hcl
environment = "dev"

# Use smaller nodes
system_node_vm_size = "Standard_D2s_v3"
user_node_vm_size   = "Standard_D4s_v3"
gpu_node_vm_size    = "Standard_NC4as_T4_v3"  # T4 GPU

# Minimal counts
system_node_count = 1
user_node_count   = 1
gpu_node_count    = 1

# Disable HA
enable_postgresql = false
enable_redis      = false
```

### Geo-Replication

Deploy to multiple regions:

```bash
# Primary region (East US)
cd terraform/azure
terraform workspace new eastus
terraform apply -var="location=eastus"

# Secondary region (West Europe)
terraform workspace new westeurope
terraform apply -var="location=westeurope"
```

## Managed Identities

### Workload Identity

Azure uses Workload Identity (similar to AWS IRSA):

```yaml
# In Kubernetes ServiceAccount
apiVersion: v1
kind: ServiceAccount
metadata:
  name: comfyui-3d-pack
  annotations:
    azure.workload.identity/client-id: "CLIENT_ID_FROM_TERRAFORM"
```

```yaml
# In Pod spec
spec:
  serviceAccountName: comfyui-3d-pack
  labels:
    azure.workload.identity/use: "true"
```

### Grant Permissions

```bash
# Get managed identity principal ID
PRINCIPAL_ID=$(terraform output -raw workload_identity_principal_id)

# Grant Storage Blob Data Contributor
az role assignment create \
  --assignee $PRINCIPAL_ID \
  --role "Storage Blob Data Contributor" \
  --scope /subscriptions/SUB_ID/resourceGroups/RG_NAME/providers/Microsoft.Storage/storageAccounts/ACCOUNT_NAME
```

## Networking

### Private Cluster

For enhanced security, make AKS private:

```hcl
# In main.tf
private_cluster_enabled = true
```

### Network Policies

Enable Azure Network Policy:

```hcl
network_profile {
  network_plugin = "azure"
  network_policy = "azure"
}
```

Apply network policies:

```bash
kubectl apply -f k8s/network-policies/
```

## Monitoring

### Container Insights

Enabled by default. View in Azure Portal:
- Navigate to AKS cluster
- Click "Insights" under Monitoring
- View metrics, logs, and recommendations

### Log Analytics Queries

```kusto
// Pod CPU usage
Perf
| where ObjectName == "K8SContainer"
| where CounterName == "cpuUsageNanoCores"
| summarize AvgCPU = avg(CounterValue) by bin(TimeGenerated, 5m), Computer

// GPU utilization
InsightsMetrics
| where Name == "gpu_utilization"
| summarize avg(Val) by bin(TimeGenerated, 5m)
```

### Application Insights

Instrument your app:

```python
from applicationinsights import TelemetryClient

tc = TelemetryClient(instrumentation_key)
tc.track_event('render_completed', {'duration': 2.5})
tc.flush()
```

## Security

### Azure AD Integration

AKS uses Azure AD for authentication:

```bash
# Get access as admin
az aks get-credentials \
  --resource-group comfyui-3d-pack-prod-rg \
  --name comfyui-aks-prod \
  --admin

# Get access as Azure AD user
az aks get-credentials \
  --resource-group comfyui-3d-pack-prod-rg \
  --name comfyui-aks-prod

# Azure AD authentication required
kubectl get pods
# Opens browser for Azure AD login
```

### RBAC

Grant users access:

```bash
# Cluster admin
az role assignment create \
  --assignee user@example.com \
  --role "Azure Kubernetes Service Cluster Admin Role" \
  --scope /subscriptions/SUB_ID/resourceGroups/RG/providers/Microsoft.ContainerService/managedClusters/CLUSTER

# Cluster user (read-only)
az role assignment create \
  --assignee user@example.com \
  --role "Azure Kubernetes Service Cluster User Role" \
  --scope SCOPE
```

### Secrets Management

Use Azure Key Vault:

```bash
# Install CSI driver
helm repo add csi-secrets-store-provider-azure https://azure.github.io/secrets-store-csi-driver-provider-azure/charts
helm install csi-secrets-store-provider-azure/csi-secrets-store-provider-azure \
  --namespace kube-system

# Create SecretProviderClass
kubectl apply -f k8s/azure-keyvault-secret-provider.yaml
```

## Backup and Disaster Recovery

### AKS Backup

Use Velero with Azure Blob Storage:

```bash
# Install Velero
velero install \
  --provider azure \
  --bucket comfyui-backups \
  --backup-location-config resourceGroup=comfyui-3d-pack-prod-rg,storageAccount=comfyuibackups \
  --snapshot-location-config resourceGroup=comfyui-3d-pack-prod-rg

# Create backup
velero backup create comfyui-backup --include-namespaces production
```

### Database Backup

Automated backups enabled:
- **Production**: 30-day retention, geo-redundant
- **Development**: 7-day retention, local

Manual backup:

```bash
az postgres flexible-server backup create \
  --resource-group comfyui-3d-pack-prod-rg \
  --name comfyui-psql-prod \
  --backup-name manual-backup
```

## Troubleshooting

### AKS Cluster Not Accessible

```bash
# Check cluster status
az aks show \
  --resource-group comfyui-3d-pack-prod-rg \
  --name comfyui-aks-prod \
  --query "powerState.code"

# Start cluster (if stopped)
az aks start \
  --resource-group comfyui-3d-pack-prod-rg \
  --name comfyui-aks-prod
```

### GPU Not Available

```bash
# Check GPU driver installation
kubectl describe nodes | grep -A 5 "nvidia.com/gpu"

# Check GPU operator
kubectl get pods -n gpu-operator

# View logs
kubectl logs -n gpu-operator -l app=nvidia-device-plugin-daemonset
```

### Storage Access Issues

```bash
# Test storage connectivity
kubectl run -it --rm az-cli --image=mcr.microsoft.com/azure-cli --restart=Never -- sh

# Inside pod
az storage blob list \
  --account-name ACCOUNT_NAME \
  --container-name models \
  --account-key KEY
```

## Cost Estimation

Production deployment (East US):

| Resource                     | Cost/Month  |
|------------------------------|-------------|
| AKS Control Plane            | $73         |
| System Nodes (3x D4s_v3)     | $600        |
| User Nodes (3x D8s_v3)       | $1,200      |
| GPU Nodes (2x NC6s_v3)       | $3,600      |
| PostgreSQL (D2s_v3)          | $150        |
| Redis (Standard, C2)         | $75         |
| Storage (1TB)                | $40         |
| Container Registry (Premium) | $167        |
| Log Analytics                | $50         |
| **Total**                    | **~$5,955** |

Savings strategies:
- Use spot instances for GPU nodes (~70% cheaper)
- Stop clusters during off-hours
- Use reserved instances for baseline load
- Optimize node sizes

## Additional Resources

- [Azure AKS Documentation](https://docs.microsoft.com/azure/aks/)
- [Azure VM Pricing](https://azure.microsoft.com/pricing/details/virtual-machines/)
- [AKS Best Practices](https://docs.microsoft.com/azure/aks/best-practices)
- [GPU on AKS](https://docs.microsoft.com/azure/aks/gpu-cluster)

## Support

For Azure-specific issues:
- Check [Azure Service Health](https://portal.azure.com/#blade/Microsoft_Azure_Health/AzureHealthBrowseBlade/serviceIssues)
- Review [AKS documentation](https://docs.microsoft.com/azure/aks/)
- Open support ticket in Azure Portal
