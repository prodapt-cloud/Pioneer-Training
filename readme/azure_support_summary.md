# Azure OpenAI Support - Summary

## ✅ What Was Changed

### 1. [`main.py`](file:///d:/Workspace/pioneer/Pioneer-Training/llmops/Lab1-LLMOps-Pipeline/app/main.py)

**Added intelligent provider selection:**
```python
def get_llm_config():
    """Priority: Azure OpenAI > OpenAI > Error"""
    azure_key = os.getenv("AZURE_OPENAI_KEY")
    azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    azure_api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")
    azure_deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o-mini")
    
    if azure_key and azure_endpoint:
        return {"provider": "azure", "model": f"azure/{azure_deployment}", ...}
    elif os.getenv("OPENAI_API_KEY"):
        return {"provider": "openai", "model": "gpt-4o-mini", ...}
    else:
        return {"provider": "none", "error": "No credentials"}
```

**Updated LLM call to use dynamic config:**
```python
llm_params = {
    "model": LLM_CONFIG["model"],
    "api_key": LLM_CONFIG["api_key"],
    ...
}
if LLM_CONFIG["provider"] == "azure":
    llm_params["api_base"] = LLM_CONFIG["api_base"]
    llm_params["api_version"] = LLM_CONFIG["api_version"]

response = litellm.completion(**llm_params)
```

### 2. [`lab1-workflow.yml`](file:///d:/Workspace/pioneer/Pioneer-Training/.github/workflows/lab1-workflow.yml)

**Added Azure endpoint to secrets:**
```yaml
kubectl create secret generic llmops-api-keys \
  --from-literal=OPENAI_API_KEY=${{ secrets.OPENAI_API_KEY }} \
  --from-literal=AZURE_OPENAI_KEY=${{ secrets.AZURE_OPENAI_KEY }} \
  --from-literal=AZURE_OPENAI_ENDPOINT=${{ secrets.AZURE_OPENAI_ENDPOINT }} \
  --from-literal=GROQ_API_KEY=${{ secrets.GROQ_API_KEY }}
```

### 3. [`deployment.yaml`](file:///d:/Workspace/pioneer/Pioneer-Training/llmops/Lab1-LLMOps-Pipeline/k8s/deployment.yaml)

**Added Azure environment variables:**
```yaml
env:
  # Secrets (from GitHub Secrets)
  - name: AZURE_OPENAI_KEY
    valueFrom:
      secretKeyRef:
        name: llmops-api-keys
        key: AZURE_OPENAI_KEY
        optional: true
  - name: AZURE_OPENAI_ENDPOINT
    valueFrom:
      secretKeyRef:
        name: llmops-api-keys
        key: AZURE_OPENAI_ENDPOINT
        optional: true
  
  # Environment Variables (configurable)
  - name: AZURE_OPENAI_API_VERSION
    value: "2024-02-15-preview"
  - name: AZURE_OPENAI_DEPLOYMENT_NAME
    value: "gpt-4o-mini"
```

---

## 🔑 GitHub Secrets to Add

Go to **Settings** → **Secrets and variables** → **Actions**:

### For Azure OpenAI:
- **Name**: `AZURE_OPENAI_KEY`  
  **Value**: Your Azure API key

- **Name**: `AZURE_OPENAI_ENDPOINT`  
  **Value**: `https://your-resource.openai.azure.com/`

### For OpenAI (fallback):
- **Name**: `OPENAI_API_KEY`  
  **Value**: Your OpenAI API key (sk-...)

---

## 🎯 Provider Selection Logic

```
IF Azure credentials exist (KEY + ENDPOINT):
    ✅ Use Azure OpenAI
ELSE IF OpenAI key exists:
    ✅ Use OpenAI
ELSE:
    ❌ Return error (503)
```

---

## 🧪 Testing

### Check which provider is active:
```bash
curl http://localhost:8080/health
```

**Response:**
```json
{
  "status": "healthy",
  "redis": "connected",
  "llm_provider": "azure",
  "llm_model": "azure/gpt-4o-mini"
}
```

### Test chat completion:
```bash
curl -X POST http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "Hello!"}]}'
```

---

## 📝 Configuration Variables

| Variable | Source | Default | Required |
|----------|--------|---------|----------|
| `AZURE_OPENAI_KEY` | GitHub Secret | - | For Azure |
| `AZURE_OPENAI_ENDPOINT` | GitHub Secret | - | For Azure |
| `AZURE_OPENAI_API_VERSION` | Env Var | `2024-02-15-preview` | No |
| `AZURE_OPENAI_DEPLOYMENT_NAME` | Env Var | `gpt-4o-mini` | No |
| `OPENAI_API_KEY` | GitHub Secret | - | For OpenAI |

---

## ✨ Features

- ✅ **Dual provider support**: Azure OpenAI + OpenAI
- ✅ **Intelligent selection**: Automatically chooses based on available credentials
- ✅ **Secure**: All keys stored in GitHub Secrets → Kubernetes Secrets
- ✅ **Configurable**: API version and deployment name via environment variables
- ✅ **Observable**: Health endpoint shows active provider
- ✅ **Graceful fallback**: Falls back to OpenAI if Azure not configured

---

## 🚀 Deploy

```bash
git add .
git commit -m "Add Azure OpenAI support with intelligent provider selection"
git push origin lab1
```

Done! 🎉
