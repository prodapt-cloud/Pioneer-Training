# Azure OpenAI Configuration Guide

## Overview

The application now supports **both OpenAI and Azure OpenAI** with intelligent provider selection:

```
Priority: Azure OpenAI > OpenAI > Error
```

If both are configured, **Azure OpenAI takes precedence**.

---

## 🔧 Configuration Summary

### Secrets (from GitHub Secrets → Kubernetes Secrets)
- `AZURE_OPENAI_KEY` - Your Azure OpenAI API key
- `AZURE_OPENAI_ENDPOINT` - Your Azure OpenAI endpoint URL

### Environment Variables (set in deployment.yaml)
- `AZURE_OPENAI_API_VERSION` - Default: `"2024-02-15-preview"`
- `AZURE_OPENAI_DEPLOYMENT_NAME` - Default: `"gpt-4o-mini"`

---

## 📋 Setup Instructions

### Step 1: Get Azure OpenAI Credentials

1. **Create Azure OpenAI Resource**:
   - Go to [Azure Portal](https://portal.azure.com)
   - Create a new **Azure OpenAI** resource
   - Wait for deployment to complete

2. **Get Your Endpoint**:
   - Go to your Azure OpenAI resource
   - Click **Keys and Endpoint**
   - Copy the **Endpoint** (e.g., `https://your-resource.openai.azure.com/`)

3. **Get Your API Key**:
   - In the same **Keys and Endpoint** section
   - Copy **KEY 1** or **KEY 2**

4. **Deploy a Model**:
   - Go to **Model deployments** → **Manage Deployments**
   - Click **Create new deployment**
   - Select model: **gpt-4o-mini** (or your preferred model)
   - Give it a deployment name (e.g., `gpt-4o-mini`)
   - Click **Create**

### Step 2: Add Secrets to GitHub

1. Go to your GitHub repository
2. **Settings** → **Secrets and variables** → **Actions**
3. Add these secrets:

   **Secret 1:**
   - Name: `AZURE_OPENAI_KEY`
   - Value: Your API key (from Step 1)

   **Secret 2:**
   - Name: `AZURE_OPENAI_ENDPOINT`
   - Value: Your endpoint URL (e.g., `https://your-resource.openai.azure.com/`)

### Step 3: Update Environment Variables (Optional)

If your deployment name or API version differs from defaults, update [`deployment.yaml`](file:///d:/Workspace/pioneer/Pioneer-Training/llmops/Lab1-LLMOps-Pipeline/k8s/deployment.yaml):

```yaml
- name: AZURE_OPENAI_API_VERSION
  value: "2024-02-15-preview"  # Change if needed
- name: AZURE_OPENAI_DEPLOYMENT_NAME
  value: "gpt-4o-mini"  # Must match your Azure deployment name
```

### Step 4: Deploy

```bash
git add .
git commit -m "Configure Azure OpenAI support"
git push origin lab1
```

---

## 🔍 How It Works

### Intelligent Provider Selection

The application checks credentials in this order:

```python
if AZURE_OPENAI_KEY and AZURE_OPENAI_ENDPOINT:
    # Use Azure OpenAI
    provider = "azure"
elif OPENAI_API_KEY:
    # Use OpenAI
    provider = "openai"
else:
    # No credentials
    provider = "none"
```

### Configuration Flow

```
GitHub Secrets
    ↓
Workflow creates Kubernetes Secret
    ↓
Deployment injects as environment variables
    ↓
main.py reads and selects provider
    ↓
LiteLLM calls appropriate API
```

### What Gets Logged

On startup, you'll see:

**If using Azure:**
```
🤖 LLM Provider: azure
   Model: azure/gpt-4o-mini
   Endpoint: https://your-resource.openai.azure.com/
   API Version: 2024-02-15-preview
```

**If using OpenAI:**
```
🤖 LLM Provider: openai
   Model: gpt-4o-mini
```

---

## ✅ Verification

### Check Health Endpoint

```bash
kubectl port-forward svc/llmops-service 8080:80
curl http://localhost:8080/health
```

**Expected response:**
```json
{
  "status": "healthy",
  "redis": "connected",
  "llm_provider": "azure",
  "llm_model": "azure/gpt-4o-mini"
}
```

### Test Chat Completion

```bash
curl -X POST http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "Hello from Azure!"}],
    "metadata": {"department": "engineering"}
  }'
```

### Check Pod Logs

```bash
kubectl logs -l app=llmops-api --tail=50
```

Look for the startup message showing which provider is configured.

---

## 🔄 Switching Between Providers

### Use Azure OpenAI
Set both secrets in GitHub:
- `AZURE_OPENAI_KEY`
- `AZURE_OPENAI_ENDPOINT`

### Use OpenAI
Only set:
- `OPENAI_API_KEY`

Remove or leave Azure secrets empty.

### Use Both (Azure takes priority)
Set all three secrets. Azure will be used automatically.

---

## 🚨 Troubleshooting

### Issue: "LLM not configured" error

**Check:**
```bash
kubectl get secret llmops-api-keys
kubectl describe secret llmops-api-keys
```

**Verify secrets exist:**
```bash
kubectl get secret llmops-api-keys -o jsonpath='{.data}' | jq
```

### Issue: "Resource not found" from Azure

**Possible causes:**
1. Wrong deployment name in `AZURE_OPENAI_DEPLOYMENT_NAME`
2. Model not deployed in Azure portal
3. Wrong endpoint URL

**Fix:**
1. Check your Azure deployment name matches exactly
2. Verify model is deployed in Azure Portal
3. Ensure endpoint URL is correct (no trailing slash)

### Issue: "API version not supported"

**Fix:**
Update `AZURE_OPENAI_API_VERSION` in deployment.yaml to a supported version:
- `2024-02-15-preview` (recommended)
- `2023-12-01-preview`
- `2023-05-15`

---

## 💰 Cost Comparison

### Azure OpenAI (Pay-as-you-go)
- **gpt-4o-mini**: ~$0.15 per 1M input tokens, ~$0.60 per 1M output tokens
- Same pricing as OpenAI
- Billed through Azure subscription

### OpenAI
- **gpt-4o-mini**: $0.150 per 1M input tokens, $0.600 per 1M output tokens
- Billed directly by OpenAI

**Both are very affordable for testing and small-scale production!**

---

## 📝 Environment Variables Reference

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `AZURE_OPENAI_KEY` | Secret | - | Azure OpenAI API key |
| `AZURE_OPENAI_ENDPOINT` | Secret | - | Azure OpenAI endpoint URL |
| `AZURE_OPENAI_API_VERSION` | Env Var | `2024-02-15-preview` | Azure API version |
| `AZURE_OPENAI_DEPLOYMENT_NAME` | Env Var | `gpt-4o-mini` | Your deployment name in Azure |
| `OPENAI_API_KEY` | Secret | - | OpenAI API key (fallback) |

---

## ✨ Summary

You now have:
- ✅ Support for both Azure OpenAI and OpenAI
- ✅ Intelligent provider selection (Azure > OpenAI)
- ✅ Secure credential management via GitHub Secrets
- ✅ Configurable API version and deployment name
- ✅ Health endpoint showing active provider
- ✅ Easy switching between providers

**Next**: Add your Azure credentials to GitHub Secrets and deploy! 🚀
