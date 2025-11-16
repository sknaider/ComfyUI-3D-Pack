# Multi-Region Deployment Guide

This guide explains how to deploy ComfyUI-3D-Pack across multiple cloud regions for global high availability, low latency, and disaster recovery.

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Supported Regions](#supported-regions)
- [Prerequisites](#prerequisites)
- [Deployment](#deployment)
- [Traffic Management](#traffic-management)
- [Data Replication](#data-replication)
- [Monitoring](#monitoring)
- [Disaster Recovery](#disaster-recovery)
- [Cost Optimization](#cost-optimization)

## Overview

Multi-region deployment provides:

- **Low Latency** - Users connect to nearest region
- **High Availability** - Automatic failover between regions
- **Disaster Recovery** - Data replicated across regions
- **Compliance** - Data residency requirements (GDPR, etc.)
- **Scalability** - Distribute load globally

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Global Load Balancer                     │
│              (Route53, Cloud DNS, Traffic Manager)          │
└─────────────────┬───────────────┬───────────────┬───────────┘
                  │               │               │
       ┌──────────▼──────┐ ┌─────▼──────┐ ┌──────▼──────┐
       │   US-EAST-1     │ │  EU-WEST-1  │ │ AP-SE-1     │
       │   (Primary)     │ │  (GDPR)     │ │ (APAC)      │
       ├─────────────────┤ ├─────────────┤ ├─────────────┤
       │ • EKS Cluster   │ │ • EKS Cluster│ │ • EKS Cluster│
       │ • S3 Bucket     │ │ • S3 Bucket  │ │ • S3 Bucket  │
       │ • RDS Primary   │ │ • RDS Replica│ │ • RDS Replica│
       │ • Redis Cluster │ │ • Redis Cluster│ │ • Redis Cluster│
       └─────────────────┘ └─────────────┘ └─────────────┘
                  │               │               │
       ┌──────────▼───────────────▼───────────────▼──────────┐
       │         Global Object Storage Replication           │
       │              (S3 Cross-Region Replication)          │
       └────────────────────────────────────────────────────┘
```

## Supported Regions

### AWS Regions

| Region Code      | Location          | Use Case                    |
|------------------|-------------------|-----------------------------|
| us-east-1        | N. Virginia       | Primary (Americas)          |
| us-west-2        | Oregon            | Secondary (Americas)        |
| eu-west-1        | Ireland           | Primary (Europe, GDPR)      |
| eu-central-1     | Frankfurt         | Secondary (Europe)          |
| ap-southeast-1   | Singapore         | Primary (Asia Pacific)      |
| ap-northeast-1   | Tokyo             | Secondary (Asia Pacific)    |

### GCP Regions

| Region Code      | Location          | AWS Equivalent              |
|------------------|-------------------|-----------------------------|
| us-east1         | South Carolina    | us-east-1                   |
| europe-west1     | Belgium           | eu-west-1                   |
| asia-southeast1  | Singapore         | ap-southeast-1              |

### Azure Regions

| Region Code      | Location          | AWS Equivalent              |
|------------------|-------------------|-----------------------------|
| eastus           | Virginia          | us-east-1                   |
| westeurope       | Netherlands       | eu-west-1                   |
| southeastasia    | Singapore         | ap-southeast-1              |

## Prerequisites

### For All Cloud Providers

1. **Kubernetes Clusters** in each target region
2. **Object Storage** buckets in each region
3. **Database** with cross-region replication
4. **DNS** provider for global load balancing
5. **Monitoring** infrastructure (Prometheus, Grafana)

### AWS-Specific

```bash
# Install AWS CLI
aws --version

# Configure credentials
aws configure

# Install eksctl
curl --silent --location "https://github.com/weaveworks/eksctl/releases/latest/download/eksctl_$(uname -s)_amd64.tar.gz" | tar xz -C /tmp
sudo mv /tmp/eksctl /usr/local/bin

# Install kubectl
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl

# Install Helm
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
```

## Deployment

### Step 1: Deploy to Primary Region (US-EAST-1)

```bash
# Create EKS cluster in us-east-1
eksctl create cluster \
  --name comfyui-us-east-1 \
  --region us-east-1 \
  --nodegroup-name gpu-nodes \
  --node-type g4dn.xlarge \
  --nodes 3 \
  --nodes-min 2 \
  --nodes-max 10 \
  --managed

# Get kubeconfig
aws eks update-kubeconfig --region us-east-1 --name comfyui-us-east-1

# Install NVIDIA device plugin
kubectl apply -f https://raw.githubusercontent.com/NVIDIA/k8s-device-plugin/v0.14.0/nvidia-device-plugin.yml

# Install AWS Load Balancer Controller
helm repo add eks https://aws.github.io/eks-charts
helm install aws-load-balancer-controller eks/aws-load-balancer-controller \
  -n kube-system \
  --set clusterName=comfyui-us-east-1

# Deploy ComfyUI-3D-Pack
helm install comfyui-us ./helm/comfyui-3d-pack \
  -f helm/comfyui-3d-pack/values-us-east-1.yaml \
  --namespace production \
  --create-namespace

# Verify deployment
kubectl get pods -n production
kubectl get ingress -n production
```

### Step 2: Deploy to Europe (EU-WEST-1)

```bash
# Create EKS cluster in eu-west-1
eksctl create cluster \
  --name comfyui-eu-west-1 \
  --region eu-west-1 \
  --nodegroup-name gpu-nodes \
  --node-type g4dn.xlarge \
  --nodes 2 \
  --nodes-min 2 \
  --nodes-max 8 \
  --managed

# Switch context
aws eks update-kubeconfig --region eu-west-1 --name comfyui-eu-west-1

# Install prerequisites
kubectl apply -f https://raw.githubusercontent.com/NVIDIA/k8s-device-plugin/v0.14.0/nvidia-device-plugin.yml

helm install aws-load-balancer-controller eks/aws-load-balancer-controller \
  -n kube-system \
  --set clusterName=comfyui-eu-west-1

# Deploy with EU-specific configuration
helm install comfyui-eu ./helm/comfyui-3d-pack \
  -f helm/comfyui-3d-pack/values-eu-west-1.yaml \
  --namespace production \
  --create-namespace

# Verify
kubectl get pods -n production
```

### Step 3: Deploy to Asia Pacific (AP-SOUTHEAST-1)

```bash
# Create EKS cluster in ap-southeast-1
eksctl create cluster \
  --name comfyui-ap-southeast-1 \
  --region ap-southeast-1 \
  --nodegroup-name gpu-nodes \
  --node-type g4dn.xlarge \
  --nodes 2 \
  --nodes-min 2 \
  --nodes-max 6 \
  --managed

# Switch context
aws eks update-kubeconfig --region ap-southeast-1 --name comfyui-ap-southeast-1

# Install prerequisites
kubectl apply -f https://raw.githubusercontent.com/NVIDIA/k8s-device-plugin/v0.14.0/nvidia-device-plugin.yml

helm install aws-load-balancer-controller eks/aws-load-balancer-controller \
  -n kube-system \
  --set clusterName=comfyui-ap-southeast-1

# Deploy with APAC configuration
helm install comfyui-apac ./helm/comfyui-3d-pack \
  -f helm/comfyui-3d-pack/values-ap-southeast-1.yaml \
  --namespace production \
  --create-namespace

# Verify
kubectl get pods -n production
```

## Traffic Management

### Option 1: AWS Route 53 Geolocation Routing

```bash
# Create hosted zone
aws route53 create-hosted-zone \
  --name api.comfyui.com \
  --caller-reference $(date +%s)

# Get load balancer DNS names
US_LB=$(kubectl get ingress -n production -o jsonpath='{.items[0].status.loadBalancer.ingress[0].hostname}')
EU_LB=$(kubectl get ingress -n production -o jsonpath='{.items[0].status.loadBalancer.ingress[0].hostname}' --context eu-west-1)
APAC_LB=$(kubectl get ingress -n production -o jsonpath='{.items[0].status.loadBalancer.ingress[0].hostname}' --context ap-southeast-1)

# Create Route 53 records with geolocation
# US traffic
aws route53 change-resource-record-sets \
  --hosted-zone-id Z1234567890ABC \
  --change-batch file://route53-us.json

# EU traffic
aws route53 change-resource-record-sets \
  --hosted-zone-id Z1234567890ABC \
  --change-batch file://route53-eu.json

# APAC traffic
aws route53 change-resource-record-sets \
  --hosted-zone-id Z1234567890ABC \
  --change-batch file://route53-apac.json
```

**route53-us.json:**
```json
{
  "Changes": [{
    "Action": "CREATE",
    "ResourceRecordSet": {
      "Name": "api.comfyui.com",
      "Type": "CNAME",
      "SetIdentifier": "US",
      "GeoLocation": {
        "ContinentCode": "NA"
      },
      "TTL": 60,
      "ResourceRecords": [{"Value": "US_LB_DNS_NAME"}]
    }
  }]
}
```

### Option 2: Global Accelerator

```bash
# Create AWS Global Accelerator
aws globalaccelerator create-accelerator \
  --name comfyui-global \
  --ip-address-type IPV4 \
  --enabled

# Add endpoint groups for each region
# This provides automatic failover and optimal routing
```

### Option 3: Cloudflare Load Balancing

```yaml
# cloudflare-lb.yaml
load_balancer:
  name: comfyui-global
  default_pool_ids:
    - us-east-1-pool
    - eu-west-1-pool
    - ap-southeast-1-pool
  geo_steering:
    enabled: true
  session_affinity: cookie

pools:
  - name: us-east-1-pool
    origins:
      - name: us-east-1
        address: api-us-east.comfyui.com
        enabled: true
    monitor_id: health-check

  - name: eu-west-1-pool
    origins:
      - name: eu-west-1
        address: api-eu.comfyui.com
        enabled: true
    monitor_id: health-check

  - name: ap-southeast-1-pool
    origins:
      - name: ap-southeast-1
        address: api-apac.comfyui.com
        enabled: true
    monitor_id: health-check
```

## Data Replication

### S3 Cross-Region Replication

```bash
# Enable versioning on source bucket
aws s3api put-bucket-versioning \
  --bucket comfyui-3d-pack-us-east-1 \
  --versioning-configuration Status=Enabled

# Create replication configuration
cat > replication.json <<EOF
{
  "Role": "arn:aws:iam::ACCOUNT_ID:role/s3-replication-role",
  "Rules": [{
    "Status": "Enabled",
    "Priority": 1,
    "DeleteMarkerReplication": { "Status": "Enabled" },
    "Filter": { "Prefix": "models/" },
    "Destination": {
      "Bucket": "arn:aws:s3:::comfyui-3d-pack-eu-west-1",
      "ReplicationTime": {
        "Status": "Enabled",
        "Time": { "Minutes": 15 }
      },
      "Metrics": {
        "Status": "Enabled",
        "EventThreshold": { "Minutes": 15 }
      }
    }
  }]
}
EOF

# Apply replication
aws s3api put-bucket-replication \
  --bucket comfyui-3d-pack-us-east-1 \
  --replication-configuration file://replication.json
```

### Database Replication (RDS)

```bash
# Create read replicas in other regions
aws rds create-db-instance-read-replica \
  --db-instance-identifier comfyui-db-eu-west-1 \
  --source-db-instance-identifier arn:aws:rds:us-east-1:ACCOUNT:db:comfyui-db \
  --db-instance-class db.r5.large \
  --region eu-west-1

aws rds create-db-instance-read-replica \
  --db-instance-identifier comfyui-db-ap-southeast-1 \
  --source-db-instance-identifier arn:aws:rds:us-east-1:ACCOUNT:db:comfyui-db \
  --db-instance-class db.r5.large \
  --region ap-southeast-1
```

### Redis Global Datastore

```bash
# Create Redis Global Datastore
aws elasticache create-global-replication-group \
  --global-replication-group-id-suffix comfyui-global \
  --primary-replication-group-id comfyui-redis-us-east-1 \
  --global-replication-group-description "ComfyUI Global Redis"

# Add secondary regions
aws elasticache create-replication-group \
  --replication-group-id comfyui-redis-eu-west-1 \
  --replication-group-description "EU Redis" \
  --global-replication-group-id comfyui-global \
  --region eu-west-1
```

## Monitoring

### Multi-Region Prometheus Federation

```yaml
# prometheus-federation.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: prometheus-federation
  namespace: monitoring
data:
  prometheus.yml: |
    global:
      scrape_interval: 30s

    scrape_configs:
      # US East 1
      - job_name: 'us-east-1'
        honor_labels: true
        metrics_path: '/federate'
        params:
          'match[]':
            - '{job="comfyui"}'
        static_configs:
          - targets:
            - 'prometheus.us-east-1.internal:9090'
            labels:
              region: us-east-1

      # EU West 1
      - job_name: 'eu-west-1'
        honor_labels: true
        metrics_path: '/federate'
        params:
          'match[]':
            - '{job="comfyui"}'
        static_configs:
          - targets:
            - 'prometheus.eu-west-1.internal:9090'
            labels:
              region: eu-west-1

      # AP Southeast 1
      - job_name: 'ap-southeast-1'
        honor_labels: true
        metrics_path: '/federate'
        params:
          'match[]':
            - '{job="comfyui"}'
        static_configs:
          - targets:
            - 'prometheus.ap-southeast-1.internal:9090'
            labels:
              region: ap-southeast-1
```

### Grafana Multi-Region Dashboard

See `monitoring/grafana/dashboards/multi-region-dashboard.json` for the complete dashboard configuration.

Key metrics to monitor:
- Request latency by region
- Error rates by region
- Cross-region replication lag
- Regional capacity and scaling
- Cost by region

## Disaster Recovery

### Failover Procedure

1. **Detect Failure**
   ```bash
   # Check region health
   curl https://api-us-east.comfyui.com/health
   ```

2. **Update DNS**
   ```bash
   # Route US traffic to EU
   aws route53 change-resource-record-sets \
     --hosted-zone-id Z1234567890ABC \
     --change-batch file://failover-to-eu.json
   ```

3. **Promote Read Replica** (if primary database fails)
   ```bash
   aws rds promote-read-replica \
     --db-instance-identifier comfyui-db-eu-west-1
   ```

4. **Verify**
   ```bash
   # Test from different locations
   curl -H "Host: api.comfyui.com" https://GLOBAL_IP/health
   ```

### Recovery Time Objective (RTO) & Recovery Point Objective (RPO)

| Component       | RTO      | RPO      | Strategy                        |
|-----------------|----------|----------|---------------------------------|
| Application     | 5 min    | 0        | Multi-region active-active      |
| Object Storage  | 1 min    | 15 min   | S3 CRR with RTC                 |
| Database        | 15 min   | 5 min    | RDS read replicas               |
| Redis Cache     | 1 min    | 1 min    | Global Datastore                |

## Cost Optimization

### Recommendations

1. **Right-size Resources** - Start small, scale based on traffic
2. **Use Spot Instances** - For non-GPU workloads
3. **Enable Autoscaling** - Scale down during off-peak hours
4. **S3 Lifecycle Policies** - Archive old outputs to Glacier
5. **Reserved Instances** - For predictable baseline load
6. **Cross-Region Transfer** - Minimize with edge caching

### Cost Monitoring

```bash
# Enable AWS Cost Explorer
# Tag resources by region and environment
kubectl label nodes --all region=us-east-1
kubectl label nodes --all environment=production

# Monitor costs
aws ce get-cost-and-usage \
  --time-period Start=2024-01-01,End=2024-01-31 \
  --granularity MONTHLY \
  --metrics BlendedCost \
  --group-by Type=TAG,Key=region
```

## Troubleshooting

### Common Issues

#### 1. High Latency Between Regions

**Symptom:** Slow cross-region replication

**Solution:**
```bash
# Enable S3 Transfer Acceleration
aws s3api put-bucket-accelerate-configuration \
  --bucket comfyui-3d-pack-us-east-1 \
  --accelerate-configuration Status=Enabled
```

#### 2. Split Brain Scenario

**Symptom:** Multiple regions think they're primary

**Solution:**
- Use Route 53 health checks with failover
- Implement distributed locks (via DynamoDB Global Tables)
- Monitor with alerting

#### 3. Data Consistency Issues

**Symptom:** Different data in different regions

**Solution:**
- Check S3 CRR status
- Verify database replication lag
- Use strong consistency reads when needed

## Next Steps

1. ✅ Deploy to multiple regions
2. ☐ Set up global load balancing
3. ☐ Configure cross-region replication
4. ☐ Implement monitoring and alerting
5. ☐ Test disaster recovery procedures
6. ☐ Document runbooks
7. ☐ Train team on multi-region operations

## References

- [AWS Multi-Region Architecture](https://aws.amazon.com/solutions/implementations/multi-region-infrastructure/)
- [Kubernetes Multi-Cluster](https://kubernetes.io/docs/concepts/cluster-administration/federation/)
- [GDPR Compliance Guide](https://gdpr.eu/)
- [Route 53 Routing Policies](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/routing-policy.html)
