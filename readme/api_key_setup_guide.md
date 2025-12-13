# 🔐 Secure API Key Setup Guide

## Overview

This guide shows you how to securely configure API keys for your LLMOps pipeline **without hardcoding them in your repository**.

## 🎯 How It Works

```
GitHub Secrets → Workflow → Kubernetes Secret → Pod Environment Variables → Application
```

1. **GitHub Secrets**: Store API keys securely in GitHub repository settings
2. **Workflow**: GitHub Actions reads secrets and creates Kubernetes secrets
3. **Kubernetes Secret**: Stores encrypted credentials in the cluster
4. **Pod Env Vars**: Deployment injects secrets as environment variables
5. **Application**: Code reads `os.getenv("OPENAI_API_KEY")`

---

## 📋 Step-by-Step Setup

### Step 1: Get Your OpenAI API Key

1. Go to [platform.openai.com](https://platform.openai.com)
2. Sign up or log in
3. Navigate to **API Keys** section
4. Click **Create new secret key**
5. Copy the key (starts with `sk-...`)
6. **Important**: Save it somewhere safe - you won't see it again!

### Step 2: Add Secret to GitHub Repository

1. Go to your GitHub repository
2. Click **Settings** (top menu)
3. In the left sidebar, click **Secrets and variables** → **Actions**
4. Click **New repository secret**
5. Fill in:
   - **Name**: `OPENAI_API_KEY`
   - **Secret**: Paste your API key (e.g., `sk-proj-...`)
6. Click **Add secret**

### Step 3: Verify the Configuration

The code is already configured to use the secret! Here's what happens:

#### In the Workflow ([lab1-workflow.yml](file:///d:/Workspace/pioneer/Pioneer-Training/.github/workflows/lab1-workflow.yml)):
```yaml
# Creates Kubernetes secret from GitHub secret
- name: Create API key secrets
  run: |
    kubectl create secret generic llmops-api-keys \
      --from-literal=OPENAI_API_KEY=${{ secrets.OPENAI_API_KEY }} \
      --dry-run=client -o yaml | kubectl apply -f -
```

#### In the Deployment ([deployment.yaml](file:///d:/Workspace/pioneer/Pioneer-Training/llmops/Lab1-LLMOps-Pipeline/k8s/deployment.yaml)):
```yaml
env:
- name: OPENAI_API_KEY
  valueFrom:
    secretKeyRef:
      name: llmops-api-keys
      key: OPENAI_API_KEY
      optional: true
```

#### In the Application ([main.py](file:///d:/Workspace/pioneer/Pioneer-Training/llmops/Lab1-LLMOps-Pipeline/app/main.py)):
```python
response = litellm.completion(
    model="gpt-4o-mini",
    api_key=os.getenv("OPENAI_API_KEY")  # Reads from environment
)
```

### Step 4: Deploy

```bash
git add .
git commit -m "Configure OpenAI API with secure secrets"
git push origin lab1
```

The workflow will:
1. ✅ Read `OPENAI_API_KEY` from GitHub Secrets
2. ✅ Create Kubernetes secret `llmops-api-keys`
3. ✅ Inject it into pods as environment variable
4. ✅ Application uses it to call OpenAI API

---

## 🔍 Verification

### Check if Secret Exists in Kubernetes

```bash
kubectl get secret llmops-api-keys
kubectl describe secret llmops-api-keys
```

### Check if Pod Has the Environment Variable

```bash
kubectl get pods
kubectl exec -it <pod-name> -- env | grep OPENAI_API_KEY
```

### Test the API

```bash
kubectl port-forward svc/llmops-service 8080:80

curl -X POST http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "Hello!"}],
    "metadata": {"department": "engineering"}
  }'
```

---

## 💰 Cost Considerations

### OpenAI gpt-4o-mini Pricing (as of Dec 2024):
- **Input**: $0.150 per 1M tokens (~$0.00015 per 1K tokens)
- **Output**: $0.600 per 1M tokens (~$0.0006 per 1K tokens)

**Example**: 1,000 requests with 500 tokens each ≈ **$0.38**

Very affordable for testing and small-scale production!

---

## 🔄 Alternative LLM Providers

### Option 1: Groq (Free Tier Available)

**Setup:**
1. Get API key from [groq.com](https://groq.com)
2. Add to GitHub Secrets as `GROQ_API_KEY`
3. Update `main.py`:
   ```python
   response = litellm.completion(
       model="groq/llama-3.2-3b-preview",
       api_key=os.getenv("GROQ_API_KEY")
   )
   ```

**Pros**: ✅ Free tier, ✅ Very fast inference  
**Cons**: ❌ Rate limits on free tier

### Option 2: Azure OpenAI

**Setup:**
1. Get Azure OpenAI credentials
2. Add to GitHub Secrets:
   - `AZURE_OPENAI_KEY`
   - `AZURE_OPENAI_ENDPOINT`
3. Update `main.py`:
   ```python
   response = litellm.completion(
       model="azure/gpt-4o-mini",
       api_key=os.getenv("AZURE_OPENAI_KEY"),
       api_base=os.getenv("AZURE_OPENAI_ENDPOINT")
   )
   ```

**Pros**: ✅ Enterprise-grade, ✅ Data residency  
**Cons**: ❌ Requires Azure subscription

---

## 🚨 Troubleshooting

### Issue: "AuthenticationError: Invalid API key"

**Solution:**
1. Verify the secret exists in GitHub: Settings → Secrets → Actions
2. Check the secret name matches exactly: `OPENAI_API_KEY`
3. Ensure the API key is valid (test it locally)
4. Re-run the workflow to recreate the Kubernetes secret

### Issue: Pod shows "OPENAI_API_KEY not set"

**Solution:**
```bash
# Check if secret exists
kubectl get secret llmops-api-keys

# If missing, create it manually
kubectl create secret generic llmops-api-keys \
  --from-literal=OPENAI_API_KEY=your-key-here

# Restart the deployment
kubectl rollout restart deployment/llmops-api
```

### Issue: "Rate limit exceeded"

**Solution:**
- You've hit OpenAI's rate limit
- Wait a few minutes or upgrade your OpenAI plan
- Consider using Groq for higher free tier limits

---

## ✅ Security Best Practices

- ✅ **Never** commit API keys to Git
- ✅ **Always** use GitHub Secrets for sensitive data
- ✅ Use `optional: true` in secretKeyRef (allows deployment without secrets for testing)
- ✅ Rotate API keys periodically
- ✅ Use different keys for dev/staging/prod
- ✅ Monitor API usage in OpenAI dashboard

---

## 📚 Summary

You now have:
1. ✅ Secure API key storage in GitHub Secrets
2. ✅ Automatic secret injection into Kubernetes
3. ✅ Application configured to use OpenAI gpt-4o-mini
4. ✅ Support for multiple LLM providers (OpenAI, Azure, Groq)
5. ✅ No hardcoded credentials in your repository

**Next**: Add your `OPENAI_API_KEY` to GitHub Secrets and deploy! 🚀
