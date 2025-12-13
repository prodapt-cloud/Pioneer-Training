# Azure "Anonymous Credentials" Error - Troubleshooting

## 🔍 Error

```
anonymous credentials error
```

This means Azure OpenAI isn't recognizing the API key.

## 🎯 Common Causes

### 1. Trailing Slash in Endpoint

**Problem**: Endpoint has trailing slash  
**Wrong**: `https://your-resource.openai.azure.com/`  
**Correct**: `https://your-resource.openai.azure.com`

**Fix**: Update GitHub secret `AZURE_OPENAI_ENDPOINT` to remove trailing slash

### 2. Wrong API Key Format

**Problem**: Using wrong key from Azure Portal

**Check**: In Azure Portal → Your OpenAI Resource → Keys and Endpoint:
- Use **KEY 1** or **KEY 2** (not the endpoint)
- Should be a long string (32+ characters)

### 3. Incorrect Deployment Name

**Problem**: `AZURE_OPENAI_DEPLOYMENT_NAME` doesn't match Azure

**Check**: In Azure Portal → Model deployments
- Note the exact deployment name
- Update in `deployment.yaml`:
  ```yaml
  - name: AZURE_OPENAI_DEPLOYMENT_NAME
    value: "your-actual-deployment-name"
  ```

### 4. Invalid API Version

**Problem**: API version not supported

**Try**: Change in `deployment.yaml`:
```yaml
- name: AZURE_OPENAI_API_VERSION
  value: "2024-02-15-preview"
```

## 📊 Next Workflow Run Will Show

The updated workflow will display:

```
=== API Pod Logs ===
AZURE_OPENAI_KEY: SET (len=64)
AZURE_OPENAI_ENDPOINT: https://...
✅ Selected: Azure OpenAI

[Error details will appear here]
```

```
=== Pod Environment Check ===
AZURE_OPENAI_KEY length: 64
AZURE_OPENAI_ENDPOINT: https://your-resource.openai.azure.com
```

## ✅ What to Check

1. **Endpoint format**: No trailing slash
2. **API key length**: Should be 32-64 characters
3. **Deployment name**: Matches Azure exactly
4. **API version**: Use `2024-02-15-preview`

## 🔧 Quick Fix Checklist

- [ ] Remove trailing slash from `AZURE_OPENAI_ENDPOINT` in GitHub Secrets
- [ ] Verify API key is correct (KEY 1 or KEY 2 from Azure)
- [ ] Check deployment name in Azure Portal
- [ ] Update `deployment.yaml` with correct deployment name
- [ ] Try API version `2024-02-15-preview`

The next workflow run will show the exact error!
