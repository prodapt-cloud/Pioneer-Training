# OpenTelemetry Tracing - Complete Guide

## ✅ **What's Been Added**

Your LLMOps API now has **distributed tracing** with OpenTelemetry!

### Trace Spans Created

Every API request creates the following trace spans:

1. **`/v1/chat/completions`** (auto-instrumented by FastAPI)
   - HTTP method, status code, duration
   - Request/response headers

2. **`cache_lookup`** (custom span)
   - Cache key generation
   - Redis lookup
   - Cache hit/miss status

3. **`render_prompt`** (custom span)
   - Jinja2 template rendering
   - Variable substitution

4. **`llm_completion`** (custom span)
   - LLM provider (openai/azure)
   - Model name
   - Temperature
   - API call duration

### Trace Attributes

Each span includes:
- `llm.provider` - openai, azure, groq
- `llm.model` - Model name
- `llm.temperature` - Temperature setting
- `cache.hit` - true/false
- `error` - Error flag and message (if error occurs)

---

## 🔗 **MLflow Integration**

**Trace IDs are logged to MLflow** for correlation!

Every MLflow run now includes:
```python
mlflow.log_param("trace_id", "a1b2c3d4e5f6...")
```

**Benefits**:
- ✅ Link MLflow metrics to distributed traces
- ✅ Debug slow requests by trace ID
- ✅ Correlate errors across systems
- ✅ Full request lineage tracking

---

## 🎯 **Configuration**

### Environment Variables

```yaml
# Enable/disable tracing
- name: OTEL_ENABLED
  value: "true"

# OTLP exporter endpoint (optional)
- name: OTEL_EXPORTER_OTLP_ENDPOINT
  value: "http://jaeger:4317"  # Or Tempo, Zipkin, etc.

# Service metadata
- name: ENVIRONMENT
  value: "production"
```

### Disable Tracing

```yaml
- name: OTEL_ENABLED
  value: "false"
```

---

## 📊 **Viewing Traces**

### Option 1: Jaeger (Recommended)

Deploy Jaeger in your cluster:

```yaml
# k8s/jaeger.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: jaeger
spec:
  replicas: 1
  selector:
    matchLabels:
      app: jaeger
  template:
    metadata:
      labels:
        app: jaeger
    spec:
      containers:
      - name: jaeger
        image: jaegertracing/all-in-one:latest
        ports:
        - containerPort: 16686  # UI
        - containerPort: 4317   # OTLP gRPC
---
apiVersion: v1
kind: Service
metadata:
  name: jaeger
spec:
  ports:
  - name: ui
    port: 16686
    targetPort: 16686
  - name: otlp
    port: 4317
    targetPort: 4317
  selector:
    app: jaeger
```

**Access**: `http://localhost:16686`

### Option 2: Grafana Tempo

```yaml
- name: OTEL_EXPORTER_OTLP_ENDPOINT
  value: "http://tempo:4317"
```

### Option 3: Console Exporter (Debug)

For local testing, traces print to console if no OTLP endpoint is set.

---

## 🔍 **Example Trace**

```
Trace ID: a1b2c3d4e5f6789012345678
├─ POST /v1/chat/completions (250ms)
│  ├─ cache_lookup (5ms)
│  │  └─ cache.hit: false
│  ├─ render_prompt (2ms)
│  └─ llm_completion (240ms)
│     ├─ llm.provider: azure
│     ├─ llm.model: gpt-4.1-mini
│     └─ llm.temperature: 0.3
```

---

## 🔗 **Correlating Traces with MLflow**

### Find Trace from MLflow Run

1. Go to MLflow UI
2. Open a run
3. Copy the `trace_id` parameter
4. Search in Jaeger/Tempo by trace ID

### Find MLflow Run from Trace

1. View trace in Jaeger
2. Copy trace ID
3. Search MLflow:
   ```python
   import mlflow
   
   client = mlflow.tracking.MlflowClient()
   runs = client.search_runs(
       experiment_id,
       filter_string=f"params.trace_id = '{trace_id}'"
   )
   ```

---

## 📈 **Use Cases**

### 1. Debug Slow Requests

**Scenario**: API response is slow

**Steps**:
1. Check MLflow for slow runs (high `total_response_time_ms`)
2. Get `trace_id` from MLflow run
3. View trace in Jaeger
4. Identify bottleneck span (cache? LLM? rendering?)

### 2. Error Investigation

**Scenario**: Request failed with 503

**Steps**:
1. Find error in MLflow (filter by `error_occurred = 1`)
2. Get `trace_id`
3. View trace to see where it failed
4. Check span attributes for error details

### 3. Cache Effectiveness

**Scenario**: Want to see cache hit patterns

**Steps**:
1. Query traces with `cache.hit = true`
2. Compare latency: cache hits vs misses
3. Optimize cache TTL based on data

### 4. Multi-Service Tracing

**Scenario**: Request spans multiple services

**Steps**:
1. Trace shows full request path
2. See latency breakdown across services
3. Identify cross-service bottlenecks

---

## 🚨 **Troubleshooting**

### Issue: No traces appearing

**Check**:
```bash
# Verify OTEL is enabled
kubectl logs -l app=llmops-api | grep "OpenTelemetry"
# Should see: ✅ OpenTelemetry tracing enabled

# Check OTLP endpoint
kubectl logs -l app=llmops-api | grep "OTLP"
```

**Solution**:
- Ensure `OTEL_ENABLED=true`
- Verify OTLP endpoint is reachable
- Check Jaeger/Tempo is running

### Issue: Traces not linked to MLflow

**Check**:
```python
# Verify trace_id is logged
run = client.get_run(run_id)
print(run.data.params.get('trace_id'))
```

**Solution**:
- Ensure both OTEL and MLflow are enabled
- Check trace context is propagated

---

## ✨ **Summary**

**What you have now**:
- ✅ Distributed tracing with OpenTelemetry
- ✅ Custom spans for cache, prompt, LLM
- ✅ Trace IDs logged to MLflow
- ✅ Full request observability
- ✅ Error tracking in traces
- ✅ Performance bottleneck identification

**View your traces**:
- Jaeger: `http://localhost:16686`
- MLflow: `http://34.71.60.197:5000` (with trace_id parameter)

**Correlation**: Every MLflow run links to its distributed trace! 🎉
