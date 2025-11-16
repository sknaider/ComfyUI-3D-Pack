# Istio Service Mesh Configuration for ComfyUI-3D-Pack

This directory contains Istio service mesh configurations for advanced traffic management, security, and observability.

## Overview

Istio provides:
- **Traffic Management**: A/B testing, canary deployments, circuit breaking
- **Security**: mTLS, authorization policies, certificate management
- **Observability**: Distributed tracing, metrics, service graphs
- **Resilience**: Retry logic, timeouts, fault injection

## Prerequisites

1. Kubernetes cluster with Istio installed
2. Istio version >= 1.19.0

## Installation

### 1. Install Istio

```bash
# Download Istio
curl -L https://istio.io/downloadIstio | sh -
cd istio-1.20.0
export PATH=$PWD/bin:$PATH

# Install Istio with demo profile (or use production profile)
istioctl install --set profile=demo -y

# Enable automatic sidecar injection for production namespace
kubectl label namespace production istio-injection=enabled
```

### 2. Apply ComfyUI Istio Configuration

```bash
# Apply all configurations
kubectl apply -f k8s/istio/

# Or apply individually
kubectl apply -f k8s/istio/gateway.yaml
kubectl apply -f k8s/istio/virtual-service.yaml
kubectl apply -f k8s/istio/destination-rule.yaml
kubectl apply -f k8s/istio/peer-authentication.yaml
kubectl apply -f k8s/istio/authorization-policy.yaml
```

## Configuration Files

### gateway.yaml
Istio Gateway for ingress traffic with TLS termination.

### virtual-service.yaml
Virtual Service for traffic routing with:
- Weighted routing for canary deployments
- Header-based routing
- Retry policies
- Timeout configuration

### destination-rule.yaml
Destination Rules for:
- Load balancing strategies
- Circuit breaking
- Connection pool settings
- Subset definitions (v1, v2, canary)

### peer-authentication.yaml
Peer Authentication for mTLS:
- STRICT mode for all services
- Ensures encrypted service-to-service communication

### authorization-policy.yaml
Authorization policies:
- Allow traffic from ingress gateway
- Allow traffic from monitoring namespace
- Deny all other traffic by default

### service-entry.yaml
Service Entries for external services:
- S3 endpoints
- External APIs
- Database connections

## Traffic Management Examples

### Canary Deployment (10% traffic to v2)

```yaml
# virtual-service.yaml
spec:
  http:
  - match:
    - headers:
        canary:
          exact: "true"
    route:
    - destination:
        host: comfyui-3d-pack
        subset: v2
  - route:
    - destination:
        host: comfyui-3d-pack
        subset: v1
      weight: 90
    - destination:
        host: comfyui-3d-pack
        subset: v2
      weight: 10
```

Apply changes:
```bash
kubectl apply -f k8s/istio/virtual-service.yaml
```

### A/B Testing (Route by user header)

```yaml
spec:
  http:
  - match:
    - headers:
        user-group:
          exact: "beta"
    route:
    - destination:
        host: comfyui-3d-pack
        subset: v2
  - route:
    - destination:
        host: comfyui-3d-pack
        subset: v1
```

### Circuit Breaking

Configured in `destination-rule.yaml`:
- Max connections: 1000
- Max pending requests: 100
- Max requests per connection: 10
- Consecutive errors before ejection: 5

## Security

### mTLS Enforcement

All service-to-service communication is encrypted:

```bash
# Verify mTLS is enabled
istioctl authn tls-check comfyui-3d-pack-xxx -n production

# Expected output: STRICT
```

### Authorization Policies

Default deny with explicit allow:

```yaml
# Allow from ingress gateway only
apiVersion: security.istio.io/v1beta1
kind: AuthorizationPolicy
metadata:
  name: allow-ingress
spec:
  selector:
    matchLabels:
      app: comfyui-3d-pack
  action: ALLOW
  rules:
  - from:
    - source:
        principals: ["cluster.local/ns/istio-system/sa/istio-ingressgateway-service-account"]
```

## Observability

### Kiali Dashboard

Access Kiali for service mesh visualization:

```bash
# Install Kiali
kubectl apply -f https://raw.githubusercontent.com/istio/istio/release-1.20/samples/addons/kiali.yaml

# Port forward
kubectl port-forward -n istio-system svc/kiali 20001:20001

# Open http://localhost:20001
```

### Jaeger Tracing

Distributed tracing is automatically configured (see ../tracing/ directory).

### Prometheus Metrics

Istio automatically exposes metrics:

```bash
# Install Prometheus
kubectl apply -f https://raw.githubusercontent.com/istio/istio/release-1.20/samples/addons/prometheus.yaml

# Query metrics
kubectl -n istio-system port-forward svc/prometheus 9090:9090
```

Key metrics:
- `istio_requests_total` - Total requests
- `istio_request_duration_milliseconds` - Request duration
- `istio_tcp_connections_opened_total` - TCP connections

### Grafana Dashboards

```bash
# Install Grafana
kubectl apply -f https://raw.githubusercontent.com/istio/istio/release-1.20/samples/addons/grafana.yaml

# Access dashboards
kubectl -n istio-system port-forward svc/grafana 3000:3000

# Open http://localhost:3000
```

Pre-configured dashboards:
- Istio Service Dashboard
- Istio Workload Dashboard
- Istio Performance Dashboard
- Istio Mesh Dashboard

## Testing

### Generate Test Traffic

```bash
# Install sample client
kubectl run -n production curl --image=curlimages/curl -it --rm --restart=Never -- sh

# Inside container
while true; do curl -s http://comfyui-3d-pack:8188/health; sleep 1; done
```

### Test Canary Deployment

```bash
# Send traffic to canary
curl -H "canary: true" http://YOUR_DOMAIN/health

# Send normal traffic
curl http://YOUR_DOMAIN/health
```

### Test Circuit Breaking

```bash
# Generate load to trigger circuit breaker
kubectl run fortio -n production --image=fortio/fortio -- load -c 10 -qps 0 -t 60s http://comfyui-3d-pack:8188/health
```

## Troubleshooting

### Check Proxy Status

```bash
# Check if proxy is running
istioctl proxy-status

# Check proxy configuration
istioctl proxy-config routes comfyui-3d-pack-xxx -n production
```

### View Logs

```bash
# View Envoy proxy logs
kubectl logs -n production comfyui-3d-pack-xxx -c istio-proxy

# View application logs
kubectl logs -n production comfyui-3d-pack-xxx -c comfyui-3d-pack
```

### Analyze Configuration

```bash
# Analyze mesh configuration
istioctl analyze -n production

# Validate configuration
istioctl validate -f k8s/istio/
```

## Performance Impact

Expected overhead:
- **Latency**: +1-2ms per request (proxy overhead)
- **CPU**: +0.5 vCPU per pod (Envoy proxy)
- **Memory**: +50MB per pod (Envoy proxy)

Optimize for production:
```yaml
# In deployment spec
resources:
  requests:
    cpu: 100m
    memory: 128Mi
  limits:
    cpu: 2000m
    memory: 1024Mi
```

## Migration Guide

### Gradual Rollout

1. **Enable injection for namespace**:
   ```bash
   kubectl label namespace production istio-injection=enabled
   ```

2. **Restart pods to inject sidecar**:
   ```bash
   kubectl rollout restart deployment comfyui-3d-pack -n production
   ```

3. **Verify sidecar injection**:
   ```bash
   kubectl get pods -n production
   # Should show 2/2 containers (app + istio-proxy)
   ```

4. **Apply Istio configs gradually**:
   ```bash
   # Start with gateway and virtual service
   kubectl apply -f k8s/istio/gateway.yaml
   kubectl apply -f k8s/istio/virtual-service.yaml

   # Then add security
   kubectl apply -f k8s/istio/peer-authentication.yaml

   # Finally add policies
   kubectl apply -f k8s/istio/authorization-policy.yaml
   ```

## Best Practices

1. **Start with permissive mTLS**, then move to STRICT
2. **Use namespace-level policies** for easier management
3. **Monitor resource usage** after enabling Istio
4. **Use virtual services** for all traffic routing
5. **Enable access logs** for debugging:
   ```bash
   istioctl install --set meshConfig.accessLogFile=/dev/stdout
   ```

## Cost Considerations

Additional costs:
- **CPU**: ~0.5 vCPU per pod for Envoy proxy
- **Memory**: ~50MB per pod for Envoy proxy
- **Control plane**: ~1 vCPU + 1GB memory

For 10 pods: ~5 vCPU + 500MB additional resources

## References

- [Istio Documentation](https://istio.io/latest/docs/)
- [Traffic Management](https://istio.io/latest/docs/tasks/traffic-management/)
- [Security](https://istio.io/latest/docs/tasks/security/)
- [Observability](https://istio.io/latest/docs/tasks/observability/)
