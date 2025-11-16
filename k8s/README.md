# Kubernetes Deployment Guide

This directory contains Kubernetes manifests for deploying ComfyUI-3D-Pack in production.

## Prerequisites

- Kubernetes 1.24+
- NVIDIA GPU Operator installed
- Cert-Manager (for TLS certificates)
- NGINX Ingress Controller
- Prometheus Operator (optional, for monitoring)
- Persistent volume provisioner

## Quick Start

### 1. Create Namespace

```bash
kubectl apply -f namespace.yaml
```

### 2. Create Secrets

```bash
# Create secrets (DO NOT use the template values!)
kubectl create secret generic comfyui-secrets \
  --from-literal=huggingface-token=YOUR_HF_TOKEN \
  --from-literal=api-keys=YOUR_API_KEY_1,YOUR_API_KEY_2 \
  -n comfyui-3d-pack
```

### 3. Create ConfigMap

```bash
kubectl apply -f configmap.yaml
```

### 4. Create Persistent Volume Claims

```bash
kubectl apply -f pvc.yaml
```

### 5. Deploy Application

```bash
kubectl apply -f deployment.yaml
kubectl apply -f service.yaml
```

### 6. Create Ingress

Edit `ingress.yaml` to set your domain, then:

```bash
kubectl apply -f ingress.yaml
```

### 7. Enable Autoscaling (Optional)

```bash
kubectl apply -f hpa.yaml
```

### 8. Enable Monitoring (Optional)

If you have Prometheus Operator installed:

```bash
kubectl apply -f servicemonitor.yaml
```

## Deployment with Single Command

```bash
kubectl apply -f .
```

**Note**: Update secrets first!

## Verify Deployment

```bash
# Check pods
kubectl get pods -n comfyui-3d-pack

# Check services
kubectl get svc -n comfyui-3d-pack

# Check ingress
kubectl get ingress -n comfyui-3d-pack

# View logs
kubectl logs -f deployment/comfyui-3d-pack -n comfyui-3d-pack

# Check health
kubectl exec -it deployment/comfyui-3d-pack -n comfyui-3d-pack -- curl http://localhost:8188/health
```

## Configuration

### Resource Limits

Edit `deployment.yaml` to adjust resource limits:

```yaml
resources:
  requests:
    memory: "8Gi"
    cpu: "2000m"
    nvidia.com/gpu: "1"
  limits:
    memory: "16Gi"
    cpu: "4000m"
    nvidia.com/gpu: "1"
```

### Replicas

Edit `deployment.yaml` or use kubectl:

```bash
kubectl scale deployment/comfyui-3d-pack --replicas=4 -n comfyui-3d-pack
```

### Autoscaling

Edit `hpa.yaml` to adjust autoscaling parameters:

```yaml
minReplicas: 2
maxReplicas: 10
```

## Storage

### Models

Models are stored in a PersistentVolume with `ReadOnlyMany` access mode, allowing sharing across pods.

**Pre-populate models:**

```bash
# Create a job to download models
kubectl apply -f - <<EOF
apiVersion: batch/v1
kind: Job
metadata:
  name: model-downloader
  namespace: comfyui-3d-pack
spec:
  template:
    spec:
      containers:
      - name: downloader
        image: comfyui-3d-pack:v0.1.7
        command: ["sh", "-c", "python download_models.py"]
        volumeMounts:
        - name: models
          mountPath: /app/models
      volumes:
      - name: models
        persistentVolumeClaim:
          claimName: comfyui-models-pvc
      restartPolicy: OnFailure
EOF
```

### Outputs

Outputs are stored in a PersistentVolume with `ReadWriteMany` access mode.

## Networking

### Ingress

The ingress configuration includes:

- TLS termination with Let's Encrypt
- Rate limiting
- Security headers
- Request timeouts

Edit `ingress.yaml` to configure your domain.

### Load Balancing

The service uses `ClientIP` session affinity to route requests from the same client to the same pod.

## Security

### Pod Security

- Runs as non-root user (UID 1001)
- Read-only root filesystem (where possible)
- Capabilities dropped
- SecurityContext enforced

### Network Policies

Create network policies to restrict traffic:

```bash
kubectl apply -f - <<EOF
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: comfyui-3d-pack
  namespace: comfyui-3d-pack
spec:
  podSelector:
    matchLabels:
      app: comfyui-3d-pack
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: ingress-nginx
    ports:
    - protocol: TCP
      port: 8188
  egress:
  - to:
    - namespaceSelector: {}
    ports:
    - protocol: TCP
      port: 443  # For model downloads
EOF
```

## Monitoring

### Metrics

Prometheus metrics are exposed at `/metrics` endpoint.

### Grafana Dashboards

Import dashboards from `../monitoring/grafana/dashboards/`

### Alerts

Configure Prometheus alerts for:

- Pod restarts
- High error rate
- GPU OOM
- High latency

## Backup

### Backup PVCs

```bash
# Using Velero
velero backup create comfyui-backup \
  --include-namespaces comfyui-3d-pack \
  --include-resources pvc,pv

# Or manual backup
kubectl exec -it <pod-name> -n comfyui-3d-pack -- \
  tar -czf /tmp/models-backup.tar.gz /app/models
kubectl cp comfyui-3d-pack/<pod-name>:/tmp/models-backup.tar.gz ./models-backup.tar.gz
```

## Troubleshooting

### Pods not starting

```bash
# Check events
kubectl describe pod <pod-name> -n comfyui-3d-pack

# Check logs
kubectl logs <pod-name> -n comfyui-3d-pack
```

### GPU not available

```bash
# Verify GPU operator
kubectl get pods -n gpu-operator

# Check node labels
kubectl describe node <node-name> | grep nvidia.com/gpu
```

### Ingress not working

```bash
# Check ingress controller
kubectl get pods -n ingress-nginx

# Check ingress
kubectl describe ingress comfyui-3d-pack -n comfyui-3d-pack

# Check service
kubectl get endpoints -n comfyui-3d-pack
```

## Updating

### Rolling Update

```bash
# Update image
kubectl set image deployment/comfyui-3d-pack \
  comfyui-3d-pack=comfyui-3d-pack:v0.2.0 \
  -n comfyui-3d-pack

# Watch rollout
kubectl rollout status deployment/comfyui-3d-pack -n comfyui-3d-pack

# Rollback if needed
kubectl rollout undo deployment/comfyui-3d-pack -n comfyui-3d-pack
```

## Cleanup

```bash
# Delete all resources
kubectl delete namespace comfyui-3d-pack

# Or selective cleanup
kubectl delete -f .
```

## Advanced Configuration

### GPU Node Pool

For cloud providers, create a dedicated GPU node pool:

**GKE:**
```bash
gcloud container node-pools create gpu-pool \
  --accelerator type=nvidia-tesla-t4,count=1 \
  --machine-type n1-standard-4 \
  --num-nodes 2 \
  --min-nodes 1 \
  --max-nodes 10 \
  --enable-autoscaling
```

**EKS:**
```bash
eksctl create nodegroup \
  --cluster my-cluster \
  --name gpu-nodes \
  --node-type g4dn.xlarge \
  --nodes 2 \
  --nodes-min 1 \
  --nodes-max 10
```

### Multi-Region Deployment

Deploy across multiple regions for high availability:

```bash
# Deploy to each region
for region in us-east1 us-west1 eu-west1; do
  kubectl apply -f . --context=$region
done
```

## Support

For issues or questions:
- GitHub Issues: https://github.com/MrForExample/ComfyUI-3D-Pack/issues
- Documentation: See ../README_ENTERPRISE.md
