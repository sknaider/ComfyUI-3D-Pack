# ArgoCD GitOps Configuration

GitOps configuration for automated deployment of ComfyUI-3D-Pack using ArgoCD.

## Overview

ArgoCD provides:
- **Declarative GitOps** - Git as single source of truth
- **Automated deployments** - Continuous delivery
- **Multi-environment** - Dev, staging, production
- **Multi-region** - Deploy to multiple clusters
- **Rollback** - Easy rollback to previous versions
- **RBAC** - Role-based access control

## Architecture

```
┌─────────────────────────────────────────────────┐
│             Git Repository (GitHub)              │
│                                                   │
│  ├─ helm/comfyui-3d-pack/                       │
│  │  ├─ Chart.yaml                               │
│  │  ├─ values.yaml                              │
│  │  ├─ values-us-east-1.yaml                    │
│  │  ├─ values-eu-west-1.yaml                    │
│  │  └─ templates/                               │
│  │                                                │
│  └─ gitops/argocd/                              │
│     ├─ application.yaml                          │
│     ├─ applicationset.yaml                       │
│     └─ project.yaml                              │
└────────────────┬────────────────────────────────┘
                 │
                 │ Git Webhook
                 │
         ┌───────▼──────────┐
         │   ArgoCD Server   │
         │   (watches git)   │
         └────────┬──────────┘
                  │
     ┌────────────┼────────────┐
     │            │             │
┌────▼───┐  ┌────▼───┐  ┌──────▼────┐
│US Cluster│ │EU Cluster│ │APAC Cluster│
│ EKS      │ │ EKS      │ │ GKE        │
└──────────┘ └──────────┘ └────────────┘
```

## Prerequisites

1. **ArgoCD installed** on management cluster:

```bash
# Install ArgoCD
kubectl create namespace argocd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

# Access ArgoCD UI
kubectl port-forward svc/argocd-server -n argocd 8080:443

# Get initial admin password
kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d
```

2. **Register clusters** (for multi-region):

```bash
# Login to ArgoCD
argocd login localhost:8080 --username admin --password <password>

# Add US cluster
argocd cluster add us-east-1-cluster --name us-east-1-cluster

# Add EU cluster
argocd cluster add eu-west-1-cluster --name eu-west-1-cluster

# Add APAC cluster
argocd cluster add ap-southeast-1-cluster --name ap-southeast-1-cluster
```

## Installation

### 1. Create Project

```bash
kubectl apply -f gitops/argocd/project.yaml
```

This creates the `comfyui` AppProject with:
- Source repository whitelist
- Destination clusters and namespaces
- RBAC roles (admin, developer, viewer)
- Sync windows for production deployments

### 2. Deploy Applications

#### Option A: Individual Applications

```bash
# Deploy to production (US)
kubectl apply -f gitops/argocd/application.yaml

# This creates applications:
# - comfyui-3d-pack-prod (US)
# - comfyui-3d-pack-eu (Europe)
# - comfyui-3d-pack-apac (Asia Pacific)
# - comfyui-3d-pack-staging
```

#### Option B: ApplicationSet (Recommended)

```bash
# Deploy using ApplicationSet for automatic multi-region
kubectl apply -f gitops/argocd/applicationset.yaml

# This automatically creates applications for all regions
```

### 3. Verify Deployment

```bash
# List applications
argocd app list

# Get application status
argocd app get comfyui-3d-pack-prod

# View sync history
argocd app history comfyui-3d-pack-prod

# Watch sync status
argocd app wait comfyui-3d-pack-prod --health
```

## Configuration Files

### application.yaml
Individual Application definitions for each environment and region:
- `comfyui-3d-pack-prod` - Production (US)
- `comfyui-3d-pack-staging` - Staging
- `comfyui-3d-pack-eu` - Europe production
- `comfyui-3d-pack-apac` - Asia Pacific production

### applicationset.yaml
ApplicationSet for automated multi-region deployment:
- **Multi-region set**: Deploys to all regions automatically
- **Environment set**: Creates dev/staging/prod environments
- **PR preview set**: Creates preview environments for pull requests

### project.yaml
AppProject configuration defining:
- Allowed source repositories
- Destination clusters
- RBAC roles and policies
- Sync windows
- Resource whitelists/blacklists

## Usage

### Manual Sync

```bash
# Sync application
argocd app sync comfyui-3d-pack-prod

# Sync specific resource
argocd app sync comfyui-3d-pack-prod --resource apps:Deployment:comfyui-3d-pack

# Hard refresh (ignore cache)
argocd app sync comfyui-3d-pack-prod --force
```

### Automatic Sync

Applications are configured for auto-sync:

```yaml
syncPolicy:
  automated:
    prune: true        # Delete resources removed from git
    selfHeal: true     # Auto-sync when cluster state drifts
    allowEmpty: false  # Prevent deleting everything
```

**Auto-sync triggers:**
- Git commit pushed to tracked branch
- Cluster state drifts from desired state
- Manual refresh requested

### Rollback

```bash
# List deployment history
argocd app history comfyui-3d-pack-prod

# Rollback to specific revision
argocd app rollback comfyui-3d-pack-prod 5

# Rollback to previous revision
argocd app rollback comfyui-3d-pack-prod
```

### Diff and Preview

```bash
# Show diff between git and cluster
argocd app diff comfyui-3d-pack-prod

# Preview manifests that will be applied
argocd app manifests comfyui-3d-pack-prod

# Local diff (before committing)
argocd app diff comfyui-3d-pack-prod --local helm/comfyui-3d-pack/
```

## Deployment Workflows

### Production Deployment

1. **Create feature branch**:
   ```bash
   git checkout -b feature/my-feature
   ```

2. **Make changes** to Helm chart or values

3. **Test locally**:
   ```bash
   helm template helm/comfyui-3d-pack -f helm/comfyui-3d-pack/values-us-east-1.yaml
   ```

4. **Commit and push**:
   ```bash
   git add .
   git commit -m "feat: add new feature"
   git push origin feature/my-feature
   ```

5. **Create pull request** on GitHub

6. **Review in preview environment** (if enabled):
   ```bash
   # Preview environment automatically created
   kubectl get app -n argocd | grep pr-
   ```

7. **Merge to main**:
   - PR approved and merged
   - ArgoCD detects change
   - Auto-syncs to production (during sync window)

8. **Monitor deployment**:
   ```bash
   argocd app wait comfyui-3d-pack-prod --health
   kubectl get pods -n production -w
   ```

### Canary Deployment

Use ArgoCD Rollouts for advanced deployment strategies:

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Rollout
metadata:
  name: comfyui-3d-pack
spec:
  strategy:
    canary:
      steps:
      - setWeight: 10   # 10% to canary
      - pause: {duration: 10m}
      - setWeight: 50   # 50% to canary
      - pause: {duration: 10m}
      - setWeight: 100  # 100% to canary
```

### Blue-Green Deployment

```yaml
strategy:
  blueGreen:
    activeService: comfyui-active
    previewService: comfyui-preview
    autoPromotionEnabled: false
```

## Multi-Region Deployment

### Automatic Multi-Region

Using ApplicationSet, deployments automatically go to all regions:

```yaml
# Commit to main branch
git add helm/comfyui-3d-pack/values.yaml
git commit -m "feat: increase memory limit"
git push origin main

# ArgoCD syncs to ALL regions automatically:
# - US East 1
# - EU West 1
# - AP Southeast 1
```

### Region-Specific Updates

Update only specific region:

```bash
# Edit region-specific values
vim helm/comfyui-3d-pack/values-eu-west-1.yaml

# Commit
git add helm/comfyui-3d-pack/values-eu-west-1.yaml
git commit -m "feat(eu): enable GDPR compliance features"
git push

# Only EU deployment syncs
argocd app wait comfyui-eu --health
```

### Rolling Update Across Regions

Update regions sequentially to minimize risk:

1. **Update staging first**:
   ```bash
   git checkout develop
   # Make changes
   git push
   # Verify in staging
   ```

2. **Update US region**:
   ```bash
   git checkout main
   git cherry-pick <commit>
   git push
   # Wait for sync and verify
   ```

3. **Update EU region** (after US is stable)

4. **Update APAC region** (after EU is stable)

## Notifications

### Slack Integration

Configure notifications for deployment events:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-notifications-cm
  namespace: argocd
data:
  service.slack: |
    token: $slack-token

  trigger.on-deployed: |
    - when: app.status.operationState.phase in ['Succeeded']
      send: [app-deployed]

  template.app-deployed: |
    message: |
      Application {{.app.metadata.name}} deployed successfully!
      Revision: {{.app.status.sync.revision}}
    slack:
      attachments: |
        [{
          "title": "{{.app.metadata.name}}",
          "title_link": "{{.context.argocdUrl}}/applications/{{.app.metadata.name}}",
          "color": "good"
        }]
```

### Email Notifications

```yaml
service.email: |
  host: smtp.gmail.com
  port: 587
  from: argocd@comfyui.com
```

## Access Control (RBAC)

### Roles

Defined in `project.yaml`:

1. **Admin**: Full access to applications and repositories
2. **Developer**: Can view and sync applications
3. **Viewer**: Read-only access

### Configure SSO

Integrate with Google, GitHub, or OIDC:

```yaml
# In argocd-cm ConfigMap
data:
  url: https://argocd.comfyui.com
  dex.config: |
    connectors:
    - type: github
      id: github
      name: GitHub
      config:
        clientID: $github-client-id
        clientSecret: $github-client-secret
        orgs:
        - name: comfyui-org
```

### Grant Access

```bash
# Add user to admin role
argocd proj role add-group comfyui admin comfyui-admins

# Add user to developer role
argocd proj role add-group comfyui developer comfyui-developers
```

## Monitoring

### Metrics

ArgoCD exposes Prometheus metrics:

```promql
# Application sync status
argocd_app_info{sync_status="Synced"}

# Sync failures
rate(argocd_app_sync_total{phase="Failed"}[5m])

# Sync duration
histogram_quantile(0.99, argocd_app_reconcile_bucket)
```

### Grafana Dashboard

Import ArgoCD dashboard:

```bash
# Dashboard ID: 14584
# https://grafana.com/grafana/dashboards/14584
```

### Health Checks

```bash
# Check application health
argocd app get comfyui-3d-pack-prod --show-operation

# Check all applications
argocd app list -o wide
```

## Troubleshooting

### Application OutOfSync

```bash
# Check diff
argocd app diff comfyui-3d-pack-prod

# Force sync
argocd app sync comfyui-3d-pack-prod --force

# Refresh cache
argocd app refresh comfyui-3d-pack-prod --hard
```

### Sync Failed

```bash
# View logs
argocd app logs comfyui-3d-pack-prod

# View events
kubectl get events -n production --sort-by='.lastTimestamp'

# Check application spec
argocd app get comfyui-3d-pack-prod -o yaml
```

### Application Degraded

```bash
# Get resource health
argocd app get comfyui-3d-pack-prod --show-health

# Check pod status
kubectl get pods -n production
kubectl describe pod <pod-name> -n production
```

## Best Practices

1. **Use ApplicationSets** for multi-region/environment deployments

2. **Enable auto-sync** for non-production environments

3. **Manual sync for production** during maintenance windows:
   ```yaml
   syncPolicy:
     automated: null  # Disable auto-sync
   ```

4. **Use sync waves** for ordered deployment:
   ```yaml
   metadata:
     annotations:
       argocd.argoproj.io/sync-wave: "1"  # Deploy first
   ```

5. **Implement health checks** for custom resources

6. **Use ignore differences** for HPA-managed resources

7. **Enable notifications** for important events

8. **Regular backups** of ArgoCD configuration:
   ```bash
   argocd admin export > backup.yaml
   ```

## Cost Considerations

ArgoCD is free and open-source. Costs are minimal:
- **ArgoCD server**: ~0.5 vCPU + 512MB RAM
- **Redis**: ~0.25 vCPU + 256MB RAM
- **Repo server**: ~0.25 vCPU + 256MB RAM

Total: ~$20-30/month for managed cluster

## References

- [ArgoCD Documentation](https://argo-cd.readthedocs.io/)
- [ApplicationSet Documentation](https://argocd-applicationset.readthedocs.io/)
- [ArgoCD Rollouts](https://argoproj.github.io/argo-rollouts/)
- [GitOps Best Practices](https://www.gitops.tech/)
