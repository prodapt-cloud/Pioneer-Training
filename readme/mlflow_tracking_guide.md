# MLflow Tracking in LLMOps API

## ✅ What's Logged

Every API request to `/v1/chat/completions` now automatically logs to MLflow:

### Parameters
- `provider` - LLM provider (openai/azure/groq)
- `model` - Model name (e.g., gpt-4o-mini, azure/gpt-4o-mini)
- `temperature` - Temperature setting (0.3)
- `max_tokens` - Max tokens (512)
- `department` - User department from metadata
- `cache_hit` - Whether response came from cache
- `api_version` - Azure API version (if using Azure)
- `api_base` - Azure endpoint (if using Azure)

### Artifacts (Text Files)
- `prompt_template.jinja2` - Raw Jinja2 template
- `rendered_prompt.txt` - Final prompt sent to LLM
- `user_message.txt` - Original user message
- `response.txt` - LLM response

### Metrics
- `llm_latency_ms` - Time for LLM API call
- `total_response_time_ms` - Total request time
- `prompt_tokens` - Input tokens used
- `completion_tokens` - Output tokens generated
- `total_tokens` - Total tokens consumed
- `response_time_ms` - Cache hit response time

### Tags
- `environment` - Always "production"
- `department` - User department

---

## 🎯 Configuration

### Environment Variables

Set in [`deployment.yaml`](file:///d:/Workspace/pioneer/Pioneer-Training/llmops/Lab1-LLMOps-Pipeline/k8s/deployment.yaml):

```yaml
- name: MLFLOW_TRACKING_URI
  value: "http://localhost:5000"  # Your MLflow server
- name: MLFLOW_ENABLED
  value: "true"  # Set to "false" to disable
```

### Disable MLflow Tracking

To disable tracking (e.g., for local testing):

```yaml
- name: MLFLOW_ENABLED
  value: "false"
```

Or set environment variable:
```bash
export MLFLOW_ENABLED=false
```

---

## 📊 Viewing Runs in MLflow UI

### Access MLflow UI

```bash
# If running locally
http://localhost:5000

# If remote
http://your-mlflow-server:5000
```

### Navigate to Experiment

1. Go to MLflow UI
2. Click **Experiments**
3. Find **"llmops-production-api"**
4. View all runs

### Example Run Details

**Run Name**: `chat-20241212-204710`

**Parameters**:
```
provider: openai
model: gpt-4o-mini
temperature: 0.3
max_tokens: 512
department: engineering
cache_hit: false
```

**Metrics**:
```
llm_latency_ms: 1234.56
total_response_time_ms: 1250.00
prompt_tokens: 150
completion_tokens: 75
total_tokens: 225
```

**Artifacts**:
- `prompt_template.jinja2` - View template
- `rendered_prompt.txt` - See exact prompt sent
- `user_message.txt` - Original question
- `response.txt` - LLM answer

---

## 🔍 Querying MLflow Data

### Python API

```python
import mlflow

mlflow.set_tracking_uri("http://localhost:5000")
client = mlflow.tracking.MlflowClient()

# Get experiment
experiment = client.get_experiment_by_name("llmops-production-api")

# Get recent runs
runs = client.search_runs(
    experiment.experiment_id,
    order_by=["start_time DESC"],
    max_results=10
)

for run in runs:
    print(f"Run ID: {run.info.run_id}")
    print(f"Model: {run.data.params.get('model')}")
    print(f"Latency: {run.data.metrics.get('llm_latency_ms')}ms")
    print(f"Tokens: {run.data.metrics.get('total_tokens')}")
    print("---")
```

### Filter by Department

```python
# Get runs for specific department
runs = client.search_runs(
    experiment.experiment_id,
    filter_string="params.department = 'engineering'",
    order_by=["start_time DESC"]
)
```

### Get Average Latency

```python
import pandas as pd

# Convert to DataFrame
data = []
for run in runs:
    data.append({
        'model': run.data.params.get('model'),
        'latency': run.data.metrics.get('llm_latency_ms'),
        'tokens': run.data.metrics.get('total_tokens'),
        'cache_hit': run.data.params.get('cache_hit') == 'True'
    })

df = pd.DataFrame(data)
print(df.groupby('model')['latency'].mean())
```

---

## 📈 Use Cases

### 1. **Performance Monitoring**

Track LLM latency over time:
```python
# Get latency trend
runs = client.search_runs(experiment.experiment_id, max_results=100)
latencies = [r.data.metrics.get('llm_latency_ms') for r in runs]
avg_latency = sum(latencies) / len(latencies)
print(f"Average latency: {avg_latency:.2f}ms")
```

### 2. **Cost Tracking**

Monitor token usage:
```python
# Calculate total tokens used
total_tokens = sum(r.data.metrics.get('total_tokens', 0) for r in runs)
print(f"Total tokens: {total_tokens:,}")

# Estimate cost (gpt-4o-mini: $0.15 per 1M input, $0.60 per 1M output)
prompt_tokens = sum(r.data.metrics.get('prompt_tokens', 0) for r in runs)
completion_tokens = sum(r.data.metrics.get('completion_tokens', 0) for r in runs)
cost = (prompt_tokens * 0.15 / 1_000_000) + (completion_tokens * 0.60 / 1_000_000)
print(f"Estimated cost: ${cost:.4f}")
```

### 3. **A/B Testing Prompts**

Compare different prompt versions:
```python
# Get runs with different prompts
runs_v1 = client.search_runs(
    experiment.experiment_id,
    filter_string="tags.prompt_version = 'v1.0'"
)
runs_v2 = client.search_runs(
    experiment.experiment_id,
    filter_string="tags.prompt_version = 'v2.0'"
)

# Compare metrics
avg_latency_v1 = sum(r.data.metrics.get('llm_latency_ms') for r in runs_v1) / len(runs_v1)
avg_latency_v2 = sum(r.data.metrics.get('llm_latency_ms') for r in runs_v2) / len(runs_v2)
```

### 4. **Cache Effectiveness**

Analyze cache hit rate:
```python
cache_hits = sum(1 for r in runs if r.data.params.get('cache_hit') == 'True')
cache_hit_rate = cache_hits / len(runs) * 100
print(f"Cache hit rate: {cache_hit_rate:.1f}%")
```

---

## 🚨 Troubleshooting

### Issue: "Failed to start MLflow run"

**Cause**: MLflow server not reachable

**Solution**:
```bash
# Check if MLflow server is running
curl http://localhost:5000/health

# Or disable MLflow temporarily
export MLFLOW_ENABLED=false
```

### Issue: No runs appearing in MLflow

**Check**:
1. Verify `MLFLOW_ENABLED=true`
2. Check `MLFLOW_TRACKING_URI` is correct
3. Ensure MLflow server is accessible from the pod
4. Check pod logs for MLflow errors:
   ```bash
   kubectl logs -l app=llmops-api --tail=50 | grep MLflow
   ```

### Issue: "Experiment not found"

**Solution**:
The experiment is created automatically on first run. If missing:
```python
import mlflow
mlflow.set_tracking_uri("http://localhost:5000")
mlflow.create_experiment("llmops-production-api")
```

---

## 🎯 Summary

**What you get**:
- ✅ Automatic logging of all LLM requests
- ✅ Full parameter and prompt tracking
- ✅ Performance metrics (latency, tokens)
- ✅ Cost tracking capabilities
- ✅ A/B testing support
- ✅ Cache effectiveness monitoring
- ✅ Graceful degradation if MLflow unavailable

**Zero code changes needed** - just set `MLFLOW_TRACKING_URI` and deploy!

**View your data**: http://localhost:5000 → Experiments → "llmops-production-api"
