# ComfyUI-3D-Pack Helm Chart

Enterprise-grade Helm chart for deploying ComfyUI-3D-Pack on Kubernetes.

## TL;DR

```bash
helm repo add comfyui-3d-pack https://example.com/charts
helm install my-comfyui comfyui-3d-pack/comfyui-3d-pack
```

## Introduction

This chart bootstraps a ComfyUI-3D-Pack deployment on a [Kubernetes](https://kubernetes.io) cluster using the [Helm](https://helm.sh) package manager.

## Prerequisites

- Kubernetes 1.24+
- Helm 3.8.0+
- PV provisioner support in the underlying infrastructure
- NVIDIA GPU Operator installed (for GPU support)
- [Optional] cert-manager for automatic TLS certificate management
- [Optional] Prometheus Operator for monitoring

## Installing the Chart

To install the chart with the release name `my-comfyui`:

```bash
helm install my-comfyui ./comfyui-3d-pack
```

The command deploys ComfyUI-3D-Pack on the Kubernetes cluster with default configuration. The [Parameters](#parameters) section lists the parameters that can be configured during installation.

## Uninstalling the Chart

To uninstall/delete the `my-comfyui` deployment:

```bash
helm delete my-comfyui
```

## Parameters

### Global parameters

| Name                      | Description                                     | Value |
| ------------------------- | ----------------------------------------------- | ----- |
| `global.imageRegistry`    | Global Docker image registry                    | `""`  |
| `global.imagePullSecrets` | Global Docker registry secret names as an array | `[]`  |
| `global.storageClass`     | Global StorageClass for Persistent Volume(s)   | `""`  |

### Common parameters

| Name                | Description                                        | Value |
| ------------------- | -------------------------------------------------- | ----- |
| `nameOverride`      | String to partially override common.names.fullname | `""`  |
| `fullnameOverride`  | String to fully override common.names.fullname     | `""`  |
| `commonLabels`      | Labels to add to all deployed objects              | `{}`  |
| `commonAnnotations` | Annotations to add to all deployed objects         | `{}`  |

### ComfyUI-3D-Pack Image parameters

| Name                | Description                           | Value               |
| ------------------- | ------------------------------------- | ------------------- |
| `image.registry`    | ComfyUI-3D-Pack image registry        | `docker.io`         |
| `image.repository`  | ComfyUI-3D-Pack image repository      | `comfyui-3d-pack`   |
| `image.tag`         | ComfyUI-3D-Pack image tag             | `0.1.7`             |
| `image.pullPolicy`  | ComfyUI-3D-Pack image pull policy     | `IfNotPresent`      |
| `image.pullSecrets` | ComfyUI-3D-Pack image pull secrets    | `[]`                |

### Deployment parameters

| Name             | Description                                  | Value           |
| ---------------- | -------------------------------------------- | --------------- |
| `replicaCount`   | Number of ComfyUI-3D-Pack replicas to deploy | `2`             |
| `updateStrategy` | ComfyUI-3D-Pack deployment strategy type     | `RollingUpdate` |

### Security parameters

| Name                                          | Description                                              | Value   |
| --------------------------------------------- | -------------------------------------------------------- | ------- |
| `podSecurityContext.enabled`                  | Enabled ComfyUI-3D-Pack pods' Security Context           | `true`  |
| `podSecurityContext.fsGroup`                  | Set ComfyUI-3D-Pack pod's Security Context fsGroup       | `1001`  |
| `containerSecurityContext.enabled`            | Enabled ComfyUI-3D-Pack containers' Security Context     | `true`  |
| `containerSecurityContext.runAsUser`          | Set ComfyUI-3D-Pack containers' Security Context runAsUser | `1001` |
| `containerSecurityContext.runAsNonRoot`       | Set non-root user                                         | `true`  |

### Application parameters

| Name                              | Description                                    | Value     |
| --------------------------------- | ---------------------------------------------- | --------- |
| `config.logLevel`                 | Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL) | `INFO` |
| `config.logFormat`                | Log format (json, text)                        | `json`    |
| `config.enableAuth`               | Enable API key authentication                  | `true`    |
| `config.maxWorkers`               | Maximum worker processes                       | `4`       |
| `config.gpuMemoryFraction`        | GPU memory fraction to use (0.0-1.0)          | `0.9`     |
| `config.requestTimeout`           | Request timeout in seconds                     | `3600`    |

### Secrets

| Name                          | Description                             | Value |
| ----------------------------- | --------------------------------------- | ----- |
| `secrets.huggingfaceToken`    | HuggingFace API token                   | `""`  |
| `secrets.apiKeys`             | Comma-separated list of API keys        | `""`  |
| `secrets.existingSecret`      | Name of existing secret to use          | `""`  |

### Service parameters

| Name                              | Description                                | Value       |
| --------------------------------- | ------------------------------------------ | ----------- |
| `service.type`                    | ComfyUI-3D-Pack service type               | `ClusterIP` |
| `service.port`                    | ComfyUI-3D-Pack service HTTP port          | `8188`      |
| `service.sessionAffinity`         | Session Affinity for Kubernetes service    | `ClientIP`  |

### Ingress parameters

| Name                       | Description                          | Value                   |
| -------------------------- | ------------------------------------ | ----------------------- |
| `ingress.enabled`          | Enable ingress record generation     | `false`                 |
| `ingress.ingressClassName` | IngressClass for ingress            | `nginx`                 |
| `ingress.hostname`         | Default host for the ingress record  | `comfyui-3d.local`      |
| `ingress.tls`              | Enable TLS configuration             | `true`                  |

### Resource requests and limits

| Name                          | Description                                    | Value              |
| ----------------------------- | ---------------------------------------------- | ------------------ |
| `resources.limits.memory`     | Memory limit                                   | `16Gi`             |
| `resources.limits.cpu`        | CPU limit                                      | `4000m`            |
| `resources.limits.nvidia.com/gpu` | GPU limit                                  | `1`                |
| `resources.requests.memory`   | Memory request                                 | `8Gi`              |
| `resources.requests.cpu`      | CPU request                                    | `2000m`            |
| `resources.requests.nvidia.com/gpu` | GPU request                              | `1`                |

### Autoscaling parameters

| Name                          | Description                              | Value   |
| ----------------------------- | ---------------------------------------- | ------- |
| `autoscaling.enabled`         | Enable Horizontal POD autoscaling        | `true`  |
| `autoscaling.minReplicas`     | Minimum number of replicas               | `2`     |
| `autoscaling.maxReplicas`     | Maximum number of replicas               | `10`    |
| `autoscaling.targetCPU`       | Target CPU utilization percentage        | `70`    |
| `autoscaling.targetMemory`    | Target Memory utilization percentage     | `80`    |

### Persistence parameters

| Name                                  | Description                          | Value            |
| ------------------------------------- | ------------------------------------ | ---------------- |
| `persistence.models.enabled`          | Enable persistence for models        | `true`           |
| `persistence.models.storageClass`     | Persistent Volume storage class      | `""`             |
| `persistence.models.accessMode`       | Persistent Volume access mode        | `ReadOnlyMany`   |
| `persistence.models.size`             | Persistent Volume size               | `100Gi`          |
| `persistence.output.enabled`          | Enable persistence for output        | `true`           |
| `persistence.output.size`             | Output Persistent Volume size        | `50Gi`           |

### Object Storage parameters

| Name                          | Description                              | Value           |
| ----------------------------- | ---------------------------------------- | --------------- |
| `objectStorage.enabled`       | Enable object storage (S3/MinIO)         | `false`         |
| `objectStorage.type`          | Object storage type (s3, minio, gcs, azure) | `s3`         |
| `objectStorage.endpoint`      | Object storage endpoint                  | `""`            |
| `objectStorage.bucket`        | Object storage bucket name               | `comfyui-3d-pack` |
| `objectStorage.region`        | Object storage region                    | `us-east-1`     |

## Configuration and installation details

### Setting up secrets

Create a Kubernetes secret with your credentials:

```bash
kubectl create secret generic comfyui-secrets \
  --from-literal=huggingface-token=YOUR_TOKEN \
  --from-literal=api-keys=YOUR_API_KEYS \
  -n default
```

Then install the chart:

```bash
helm install my-comfyui ./comfyui-3d-pack \
  --set secrets.existingSecret=comfyui-secrets
```

### Enabling Ingress

```bash
helm install my-comfyui ./comfyui-3d-pack \
  --set ingress.enabled=true \
  --set ingress.hostname=comfyui.yourdomain.com \
  --set ingress.tls=true
```

### Enabling Redis

```bash
helm install my-comfyui ./comfyui-3d-pack \
  --set redis.enabled=true \
  --set redis.auth.password=YOUR_REDIS_PASSWORD
```

### Enabling Object Storage (S3)

```bash
helm install my-comfyui ./comfyui-3d-pack \
  --set objectStorage.enabled=true \
  --set objectStorage.type=s3 \
  --set objectStorage.bucket=my-bucket \
  --set objectStorage.region=us-east-1 \
  --set objectStorage.accessKey=YOUR_ACCESS_KEY \
  --set objectStorage.secretKey=YOUR_SECRET_KEY
```

### Using a custom values file

Create a `values-prod.yaml`:

```yaml
replicaCount: 5

image:
  tag: "0.1.7"

config:
  logLevel: INFO
  enableAuth: true

ingress:
  enabled: true
  hostname: api.comfyui.com
  tls: true

autoscaling:
  enabled: true
  minReplicas: 3
  maxReplicas: 20

redis:
  enabled: true

objectStorage:
  enabled: true
  type: s3
  bucket: prod-comfyui-models
```

Install with custom values:

```bash
helm install my-comfyui ./comfyui-3d-pack -f values-prod.yaml
```

## Upgrading

To upgrade the release:

```bash
helm upgrade my-comfyui ./comfyui-3d-pack
```

## Troubleshooting

### Check pod status

```bash
kubectl get pods -l app.kubernetes.io/name=comfyui-3d-pack
```

### View logs

```bash
kubectl logs -l app.kubernetes.io/name=comfyui-3d-pack -f
```

### Describe pod

```bash
kubectl describe pod <pod-name>
```

## License

Apache 2.0 License
