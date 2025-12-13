# MLflow Prompt Versioning Implementation Plan

## Goal

Add MLflow prompt versioning to the GitHub Actions workflow to track and register prompt template versions used in each deployment. This enables prompt lineage tracking, A/B testing, and rollback capabilities.

## User Review Required

> [!IMPORTANT]
> **MLflow Server Required**: This implementation assumes you have an MLflow tracking server available. 
> 
> **Questions:**
> 1. Do you have an MLflow server running? If so, what's the tracking URI?
> 2. Should we deploy MLflow as part of this workflow, or connect to an existing server?
> 3. Do you want to version both prompt templates (`assistant_v1.jinja2` and `assistant_v1.1_strict_json.jinja2`)?

## Proposed Changes

### Component: MLflow Prompt Registration Script

#### [NEW] [register_prompt.py](file:///d:/Workspace/pioneer/Pioneer-Training/llmops/Lab1-LLMOps-Pipeline/app/register_prompt.py)

Create a Python script to register prompt templates with MLflow:

```python
import mlflow
import os
from pathlib import Path
import hashlib

def register_prompt_version(prompt_path, version, tags=None):
    """Register a prompt template with MLflow"""
    # Read prompt content
    with open(prompt_path, 'r') as f:
        prompt_content = f.read()
    
    # Generate content hash for versioning
    content_hash = hashlib.sha256(prompt_content.encode()).hexdigest()[:8]
    
    # Log prompt as artifact
    with mlflow.start_run(run_name=f"prompt-{version}"):
        mlflow.log_text(prompt_content, f"prompts/{Path(prompt_path).name}")
        mlflow.log_param("prompt_version", version)
        mlflow.log_param("content_hash", content_hash)
        mlflow.log_param("file_name", Path(prompt_path).name)
        
        if tags:
            mlflow.set_tags(tags)
        
        run_id = mlflow.active_run().info.run_id
        print(f"✅ Registered prompt version {version} (run_id: {run_id})")
        return run_id
```

---

### Component: GitHub Actions Workflow

#### [MODIFY] [lab1-workflow.yml](file:///d:/Workspace/pioneer/Pioneer-Training/.github/workflows/lab1-workflow.yml)

Add a new step after building the Docker image to register prompts with MLflow:

**Location**: After step 5 (Build and push), before step 6 (Create Kind Cluster)

```yaml
# 5b. Register prompts with MLflow
- name: Register Prompt Version with MLflow
  run: |
    # Install MLflow
    pip install mlflow
    
    # Set MLflow tracking URI (use environment variable or default to local)
    export MLFLOW_TRACKING_URI=${{ secrets.MLFLOW_TRACKING_URI || 'http://localhost:5000' }}
    
    # Register the prompt
    cd llmops/Lab1-LLMOps-Pipeline/app
    python -c "
    import mlflow
    import os
    from pathlib import Path
    import hashlib
    from datetime import datetime
    
    # Read prompt
    prompt_path = 'prompt/assistant_v1.jinja2'
    with open(prompt_path, 'r') as f:
        prompt_content = f.read()
    
    # Extract version from prompt file
    version = 'v1.0.0'  # Can be parsed from file or git tag
    content_hash = hashlib.sha256(prompt_content.encode()).hexdigest()[:8]
    
    # Register with MLflow
    mlflow.set_experiment('llmops-prompts')
    with mlflow.start_run(run_name=f'prompt-{version}-{content_hash}'):
        mlflow.log_text(prompt_content, 'prompts/assistant_v1.jinja2')
        mlflow.log_param('prompt_version', version)
        mlflow.log_param('content_hash', content_hash)
        mlflow.log_param('deployment_time', datetime.now().isoformat())
        mlflow.log_param('git_sha', os.getenv('GITHUB_SHA', 'unknown'))
        mlflow.set_tag('deployment', 'production')
        mlflow.set_tag('model', 'gpt-4o-mini')
        
        run_id = mlflow.active_run().info.run_id
        print(f'✅ Registered prompt version {version} (run_id: {run_id})')
        print(f'📊 MLflow UI: {os.getenv(\"MLFLOW_TRACKING_URI\")}/experiments/1/runs/{run_id}')
    "
  env:
    MLFLOW_TRACKING_URI: ${{ secrets.MLFLOW_TRACKING_URI }}
```

---

### Component: GitHub Secrets

Add MLflow tracking URI to GitHub Secrets:

**Secret Name**: `MLFLOW_TRACKING_URI`  
**Value**: Your MLflow server URL (e.g., `http://10.128.15.238:5000` or `https://mlflow.yourcompany.com`)

---

### Component: Deployment Configuration (Optional)

#### [MODIFY] [deployment.yaml](file:///d:/Workspace/pioneer/Pioneer-Training/llmops/Lab1-LLMOps-Pipeline/k8s/deployment.yaml)

Add environment variable to track which prompt version is deployed:

```yaml
env:
  - name: PROMPT_VERSION
    value: "v1.0.0"
  - name: MLFLOW_TRACKING_URI
    value: "http://mlflow-service:5000"  # If MLflow is in the cluster
```

---

## Verification Plan

### Automated Tests

**1. Verify Prompt Registration Script**

```bash
# Test the registration locally
cd llmops/Lab1-LLMOps-Pipeline/app
export MLFLOW_TRACKING_URI=http://localhost:5000
python -c "
import mlflow
mlflow.set_experiment('test-prompts')
with mlflow.start_run():
    mlflow.log_text('test prompt', 'test.txt')
    print('✅ MLflow connection works')
"
```

**2. Check Workflow Execution**

After pushing changes:
1. Go to GitHub Actions
2. Watch the "Register Prompt Version with MLflow" step
3. Verify it completes successfully
4. Check the output for the MLflow run ID

### Manual Verification

**1. Verify in MLflow UI**

```bash
# Access MLflow UI
# If local: http://localhost:5000
# If remote: Use your MLFLOW_TRACKING_URI

# Navigate to:
# 1. Experiments → "llmops-prompts"
# 2. Find the latest run
# 3. Verify:
#    - Prompt content is logged as artifact
#    - Parameters include: prompt_version, content_hash, git_sha
#    - Tags include: deployment=production, model=gpt-4o-mini
```

**2. Verify Prompt Lineage**

```bash
# Query MLflow for prompt history
mlflow experiments search --experiment-name llmops-prompts

# Get specific run details
mlflow runs describe --run-id <run-id-from-workflow>
```

**3. Test Prompt Retrieval**

```python
# Verify you can retrieve the prompt from MLflow
import mlflow

mlflow.set_tracking_uri("http://localhost:5000")
client = mlflow.tracking.MlflowClient()

# Get latest prompt version
experiment = client.get_experiment_by_name("llmops-prompts")
runs = client.search_runs(experiment.experiment_id, order_by=["start_time DESC"], max_results=1)

if runs:
    run_id = runs[0].info.run_id
    artifact_path = client.download_artifacts(run_id, "prompts/assistant_v1.jinja2")
    with open(artifact_path, 'r') as f:
        print(f.read())
```

---

## Implementation Notes

1. **MLflow Server**: If you don't have an MLflow server, we can add a step to deploy one in the Kind cluster
2. **Version Extraction**: Currently hardcoded as `v1.0.0`, but can be extracted from:
   - Git tags
   - Prompt file comments
   - Separate version file
3. **Multiple Prompts**: Can extend to register both `assistant_v1.jinja2` and `assistant_v1.1_strict_json.jinja2`
4. **Experiment Naming**: Using `llmops-prompts` as the experiment name, can be customized

---

## Summary

This implementation adds MLflow prompt versioning to track:
- ✅ Prompt template content and versions
- ✅ Deployment timestamps and Git SHAs
- ✅ Content hashes for change detection
- ✅ Model and deployment tags

This enables prompt lineage tracking, A/B testing, and easy rollback to previous prompt versions.
