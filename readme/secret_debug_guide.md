# Secret Debug Logging - Complete Guide

## ✅ Debug Checkpoints Added

Your pipeline now has **comprehensive debug logging** at every step of the secret flow:

```
GitHub Secrets → Kubernetes Secrets → Pod Env Vars → Application
     ✓                ✓                    ✓              ✓
  Checkpoint 1     Checkpoint 2        Checkpoint 3   Checkpoint 4
```

---

## 🔍 Checkpoint 1: GitHub Secrets

**Location**: Workflow step "Create API key secrets"

**What's Logged**:
```
=== Checking GitHub Secrets (masked) ===
OPENAI_API_KEY: SET
AZURE_OPENAI_KEY: SET
AZURE_OPENAI_ENDPOINT: SET
GROQ_API_KEY: NOT SET
```

**What to Check**:
- ✅ Each secret should show "SET" if configured in GitHub
- ❌ "NOT SET" means the secret isn't in GitHub Settings → Secrets

---

## 🔍 Checkpoint 2: Kubernetes Secrets

**Location**: Workflow step "Create API key secrets"

**What's Logged**:
```
=== Verifying Kubernetes Secret ===
[
  "AZURE_OPENAI_ENDPOINT",
  "AZURE_OPENAI_KEY",
  "GROQ_API_KEY",
  "OPENAI_API_KEY"
]
```

**What to Check**:
- ✅ All expected keys should appear in the list
- ❌ Missing keys mean the secret wasn't created properly

---

## 🔍 Checkpoint 3: Pod Environment Variables

**Location**: Workflow step "Verify Pod Environment Variables"

**What's Logged**:
```
=== Checking Pod Environment Variables ===
Pod: llmops-api-698b497fb9-abc123
Checking if API keys are set (values masked):
OPENAI_API_KEY: SET
AZURE_OPENAI_KEY: SET
AZURE_OPENAI_ENDPOINT: SET

=== Pod Startup Logs ===
🔍 LLM Configuration Debug
AZURE_OPENAI_KEY: SET (len=64)
AZURE_OPENAI_ENDPOINT: https://your-resource.openai.azure.com/
✅ Selected: Azure OpenAI
```

**What to Check**:
- ✅ Environment variables should show "SET"
- ✅ Pod logs should show "Selected: Azure OpenAI" or "Selected: OpenAI"
- ❌ "NOT SET" means the secret isn't being injected into the pod

---

## 🔍 Checkpoint 4: Application Startup

**Location**: Pod logs (visible in workflow and `kubectl logs`)

**What's Logged**:
```
============================================================
🔍 LLM Configuration Debug
============================================================
AZURE_OPENAI_KEY: SET (len=64)
AZURE_OPENAI_ENDPOINT: https://your-resource.openai.azure.com/
AZURE_OPENAI_API_VERSION: 2025-01-01-preview
AZURE_OPENAI_DEPLOYMENT_NAME: gpt-4.1-mini
OPENAI_API_KEY: NOT SET
============================================================
✅ Selected: Azure OpenAI
```

**What to Check**:
- ✅ Should show "Selected: Azure OpenAI" or "Selected: OpenAI"
- ❌ "No LLM credentials found!" means secrets aren't reaching the app

---

## 🚨 Common Issues & Solutions

### Issue 1: GitHub Secrets Show "NOT SET"

**Cause**: Secrets not configured in GitHub

**Solution**:
1. Go to GitHub repository
2. Settings → Secrets and variables → Actions
3. Add secrets:
   - `OPENAI_API_KEY`
   - `AZURE_OPENAI_KEY`
   - `AZURE_OPENAI_ENDPOINT`

---

### Issue 2: Kubernetes Secret Missing Keys

**Cause**: Secret creation failed or secrets are empty

**Check Workflow Logs**:
```bash
# Look for this section in workflow logs
=== Verifying Kubernetes Secret ===
```

**Solution**:
- Ensure GitHub secrets are set (Checkpoint 1)
- Check for kubectl errors in workflow logs

---

### Issue 3: Pod Env Vars Show "NOT SET"

**Cause**: Deployment not referencing secrets correctly

**Check**:
```yaml
# deployment.yaml should have:
env:
- name: AZURE_OPENAI_KEY
  valueFrom:
    secretKeyRef:
      name: llmops-api-keys
      key: AZURE_OPENAI_KEY
      optional: true
```

**Solution**:
- Verify `deployment.yaml` has correct secret references
- Ensure secret name matches: `llmops-api-keys`
- Restart deployment: `kubectl rollout restart deployment/llmops-api`

---

### Issue 4: Application Shows "No LLM credentials found"

**Cause**: Environment variables not set in pod

**Debug**:
```bash
# Check pod environment
kubectl exec <pod-name> -- env | grep -E "(OPENAI|AZURE)"
```

**Solution**:
1. Verify Checkpoint 3 passes
2. Check pod logs for startup errors
3. Ensure secrets are created before deployment

---

## 📊 Example: Successful Flow

```
Checkpoint 1: GitHub Secrets
✅ AZURE_OPENAI_KEY: SET
✅ AZURE_OPENAI_ENDPOINT: SET

Checkpoint 2: Kubernetes Secret
✅ Keys: ["AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_KEY", ...]

Checkpoint 3: Pod Environment
✅ AZURE_OPENAI_KEY: SET
✅ AZURE_OPENAI_ENDPOINT: SET

Checkpoint 4: Application
✅ Selected: Azure OpenAI
🤖 LLM Provider: azure
   Model: azure/gpt-4.1-mini
   Endpoint: https://your-resource.openai.azure.com/
```

---

## 📊 Example: Failed Flow (Missing Secrets)

```
Checkpoint 1: GitHub Secrets
❌ AZURE_OPENAI_KEY: NOT SET
❌ AZURE_OPENAI_ENDPOINT: NOT SET

Checkpoint 2: Kubernetes Secret
⚠️  Keys: ["AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_KEY"]
    (but values are empty)

Checkpoint 3: Pod Environment
❌ AZURE_OPENAI_KEY: NOT SET
❌ AZURE_OPENAI_ENDPOINT: NOT SET

Checkpoint 4: Application
❌ No LLM credentials found!
   Please set either:
   - OPENAI_API_KEY, OR
   - AZURE_OPENAI_KEY + AZURE_OPENAI_ENDPOINT
```

---

## 🔧 Manual Verification Commands

### Check GitHub Secrets (in workflow)
Already automated in step "Create API key secrets"

### Check Kubernetes Secret
```bash
kubectl get secret llmops-api-keys
kubectl describe secret llmops-api-keys
kubectl get secret llmops-api-keys -o jsonpath='{.data}' | jq
```

### Check Pod Environment
```bash
POD=$(kubectl get pods -l app=llmops-api -o jsonpath='{.items[0].metadata.name}')
kubectl exec $POD -- env | grep -E "(OPENAI|AZURE)"
```

### Check Application Logs
```bash
kubectl logs $POD | grep "LLM Configuration"
```

---

## ✨ Summary

**Debug logging added at**:
1. ✅ GitHub Secrets verification
2. ✅ Kubernetes Secret creation
3. ✅ Pod environment variable injection
4. ✅ Application startup configuration

**Next workflow run will show**:
- Which secrets are configured in GitHub
- Which keys exist in Kubernetes
- Which env vars are set in the pod
- Which LLM provider is selected

**Look for**: The "LLM Configuration Debug" section in pod logs to see exactly what the application detects!
