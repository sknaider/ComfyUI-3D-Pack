# Distributed Tracing with Jaeger

This directory contains Jaeger configuration for distributed tracing in ComfyUI-3D-Pack.

## Overview

Jaeger provides:
- **End-to-end request tracing** across microservices
- **Performance analysis** - identify bottlenecks
- **Dependency analysis** - understand service dependencies
- **Root cause analysis** - debug complex issues
- **Service mesh integration** - works with Istio

## Architecture

```
┌─────────────────────────────────────────────────┐
│                  User Request                    │
└────────────────┬────────────────────────────────┘
                 │
         ┌───────▼──────┐
         │ Istio Gateway │
         │  (auto-traced)│
         └───────┬───────┘
                 │
         ┌───────▼───────┐
         │  ComfyUI Pod   │
         │ + Envoy Proxy  │───────┐
         │  (auto-traced) │       │ Spans
         └───────┬────────┘       │
                 │                │
         ┌───────▼────────┐       │
         │  Redis/DB      │       │
         │  (traced)      │───────┤
         └────────────────┘       │
                                  │
                         ┌────────▼─────────┐
                         │ Jaeger Collector │
                         │   (receives)     │
                         └────────┬─────────┘
                                  │
                         ┌────────▼──────────┐
                         │  Elasticsearch    │
                         │   (stores)        │
                         └────────┬──────────┘
                                  │
                         ┌────────▼──────────┐
                         │   Jaeger Query    │
                         │      (UI)         │
                         └───────────────────┘
```

## Prerequisites

1. **Kubernetes cluster** with Istio installed
2. **Jaeger Operator** installed:

```bash
# Install Jaeger Operator
kubectl create namespace observability
kubectl apply -f https://github.com/jaegertracing/jaeger-operator/releases/download/v1.51.0/jaeger-operator.yaml -n observability

# Verify installation
kubectl get pods -n observability
```

3. **Elasticsearch** (for production) or **In-Memory** (for dev)

## Installation

### Production Deployment (with Elasticsearch)

```bash
# Apply Jaeger configuration
kubectl apply -f k8s/tracing/jaeger.yaml

# Verify deployment
kubectl get jaeger -n tracing
kubectl get pods -n tracing

# Check collector endpoint
kubectl get svc -n tracing | grep collector
```

### Development Deployment (All-in-One)

For development, use simpler all-in-one deployment:

```bash
kubectl apply -f - <<EOF
apiVersion: jaegertracing.io/v1
kind: Jaeger
metadata:
  name: jaeger-dev
  namespace: tracing
spec:
  strategy: allInOne
  allInOne:
    image: jaegertracing/all-in-one:latest
    options:
      memory:
        max-traces: 10000
  storage:
    type: memory
  ingress:
    enabled: true
    hosts:
      - jaeger-dev.local
EOF
```

## Accessing Jaeger UI

### Port Forward (Development)

```bash
# Port forward Jaeger Query UI
kubectl port-forward -n tracing svc/jaeger-query 16686:16686

# Open browser
open http://localhost:16686
```

### Ingress (Production)

Access via configured domain: https://jaeger.comfyui.com

## Configuration

### Sampling Rate

Control what percentage of requests are traced:

```yaml
# 100% sampling (development)
apiVersion: telemetry.istio.io/v1alpha1
kind: Telemetry
metadata:
  name: jaeger-tracing
  namespace: istio-system
spec:
  tracing:
  - providers:
    - name: jaeger
    randomSamplingPercentage: 100.0

# 1% sampling (production - cost reduction)
randomSamplingPercentage: 1.0

# Adaptive sampling (smart - recommended)
randomSamplingPercentage: 10.0
customTags:
  priority:
    environment:
      name: TRACE_PRIORITY
      defaultValue: "normal"
```

Apply changes:
```bash
kubectl apply -f k8s/tracing/jaeger.yaml
kubectl rollout restart deployment -n istio-system
```

### Custom Tags

Add custom metadata to traces:

```yaml
customTags:
  user_id:
    header:
      name: x-user-id
  request_type:
    header:
      name: x-request-type
  version:
    literal:
      value: "v0.2.0"
  region:
    environment:
      name: AWS_REGION
```

## Using Jaeger

### Search for Traces

1. **By Service**: Select service from dropdown
2. **By Operation**: Filter specific operations (e.g., `/api/render`)
3. **By Tags**: Search by custom tags
4. **By Duration**: Find slow requests

### Analyzing Traces

**Trace View:**
- **Timeline**: See request flow through services
- **Spans**: Individual operations
- **Duration**: Time spent in each service
- **Tags**: Metadata attached to spans
- **Logs**: Events during request

**Example Trace:**
```
Trace: POST /api/render (total: 2.5s)
  ├─ istio-gateway (50ms)
  ├─ comfyui-render (2.3s)
  │  ├─ load-model (800ms)
  │  ├─ gpu-inference (1.2s)
  │  └─ save-output (300ms)
  └─ s3-upload (150ms)
```

### Common Use Cases

#### 1. Find Slow Requests

```
Service: comfyui-3d-pack
Min Duration: 5s
Limit: 100
```

#### 2. Debug Errors

```
Service: comfyui-3d-pack
Tags: error=true
```

#### 3. Analyze Dependencies

Use **Dependency Graph** to visualize:
- Which services call each other
- Request volume between services
- Error rates

#### 4. Compare Performance

Select two traces to compare:
- Before/after optimization
- Different request types
- Different regions

## Integration with Application Code

### Python OpenTelemetry

Add tracing to ComfyUI code:

```python
from opentelemetry import trace
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

# Configure tracer
resource = Resource(attributes={
    "service.name": "comfyui-3d-pack",
    "service.version": "0.2.0"
})

provider = TracerProvider(resource=resource)
jaeger_exporter = JaegerExporter(
    agent_host_name="jaeger-agent.tracing.svc.cluster.local",
    agent_port=6831,
)
provider.add_span_processor(BatchSpanProcessor(jaeger_exporter))
trace.set_tracer_provider(provider)

tracer = trace.get_tracer(__name__)

# Use tracer
@tracer.start_as_current_span("render_image")
def render_image(prompt):
    with tracer.start_as_current_span("load_model"):
        model = load_model()

    with tracer.start_as_current_span("gpu_inference"):
        result = model.infer(prompt)

    with tracer.start_as_current_span("save_output"):
        save(result)

    return result
```

Install dependencies:
```bash
pip install opentelemetry-api opentelemetry-sdk opentelemetry-exporter-jaeger
```

### Automatic Instrumentation

For automatic tracing without code changes (via Istio):

```yaml
# In pod annotations
annotations:
  sidecar.istio.io/inject: "true"
  proxy.istio.io/config: |
    tracing:
      sampling: 100
      custom_tags:
        app_version:
          literal:
            value: "v0.2.0"
```

## Monitoring and Alerts

### Key Metrics

Monitor these metrics in Prometheus:

```promql
# Trace collection rate
sum(rate(jaeger_collector_spans_received_total[5m]))

# Dropped traces
sum(rate(jaeger_collector_spans_dropped_total[5m]))

# Query latency
histogram_quantile(0.99, jaeger_query_latency_bucket)

# Storage capacity
jaeger_collector_queue_capacity - jaeger_collector_queue_length
```

### Alerts

```yaml
# prometheus-alerts.yaml
groups:
- name: jaeger
  rules:
  - alert: JaegerCollectorDroppingTraces
    expr: rate(jaeger_collector_spans_dropped_total[5m]) > 10
    for: 5m
    annotations:
      summary: "Jaeger collector dropping traces"
      description: "Collector is dropping {{ $value }} spans/sec"

  - alert: JaegerStorageFull
    expr: jaeger_collector_queue_length / jaeger_collector_queue_capacity > 0.9
    for: 10m
    annotations:
      summary: "Jaeger storage nearly full"
```

## Performance Impact

Expected overhead:
- **Latency**: +1-3ms per request
- **CPU**: +50m per pod (agent)
- **Memory**: +100MB per pod
- **Network**: ~1KB per trace

### Optimize for Production

1. **Reduce sampling rate**:
   ```yaml
   randomSamplingPercentage: 1.0  # Only 1% of requests
   ```

2. **Adaptive sampling**: Sample errors and slow requests more

3. **Use persistent storage**: Elasticsearch instead of memory

4. **Enable index cleanup**: Auto-delete old traces
   ```yaml
   esIndexCleaner:
     enabled: true
     numberOfDays: 7
   ```

## Troubleshooting

### No Traces Appearing

1. **Check collector is running**:
   ```bash
   kubectl get pods -n tracing | grep collector
   kubectl logs -n tracing -l app=jaeger -c jaeger-collector
   ```

2. **Verify Istio configuration**:
   ```bash
   kubectl get telemetry -n istio-system
   istioctl dashboard envoy deployment/comfyui-3d-pack
   # Check tracing configuration
   ```

3. **Check service connectivity**:
   ```bash
   kubectl run -n production curl --image=curlimages/curl -it --rm -- \
     curl jaeger-collector.tracing.svc.cluster.local:14268
   ```

### High Memory Usage

1. **Reduce sampling**:
   ```yaml
   randomSamplingPercentage: 1.0
   ```

2. **Increase collector replicas**:
   ```yaml
   collector:
     replicas: 5
   ```

3. **Enable auto-scaling**:
   ```yaml
   collector:
     autoscale: true
     maxReplicas: 10
   ```

### Elasticsearch Issues

1. **Check Elasticsearch health**:
   ```bash
   kubectl exec -n tracing elasticsearch-0 -- curl -s http://localhost:9200/_cluster/health
   ```

2. **Increase storage**:
   ```bash
   kubectl edit pvc -n tracing data-elasticsearch-0
   # Increase storage size
   ```

## Cost Optimization

1. **Sampling**: Only trace 1-10% in production
2. **Retention**: Keep traces for 7-30 days only
3. **Storage**: Use S3/GCS for long-term storage
4. **Compress**: Enable compression in Elasticsearch

Estimated costs:
- **Development**: ~$20/month (in-memory)
- **Production (1% sampling)**: ~$100/month (ES cluster)
- **Production (100% sampling)**: ~$500/month (larger ES)

## References

- [Jaeger Documentation](https://www.jaegertracing.io/docs/)
- [OpenTelemetry](https://opentelemetry.io/)
- [Istio Tracing](https://istio.io/latest/docs/tasks/observability/distributed-tracing/)
- [Jaeger Operator](https://github.com/jaegertracing/jaeger-operator)
