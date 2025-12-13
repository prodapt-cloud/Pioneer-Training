# Quick Fix: InvalidImageName Error

## The Problem
```
Error: InvalidImageName
couldn't parse image name "ghcr.io/${{ github.repository }}/llmops-api:latest": invalid reference format
```

The template variable `${{ github.repository }}` wasn't being substituted, causing Kubernetes to try pulling an image with a literal `${{ github.repository }}` in the name.

## The Solution

### Updated Workflow Step (Using yq with Multi-Document Support)

The workflow now uses `yq eval-all` to properly handle multi-document YAML files (Deployment + Service):

```yaml
# 7. Substitute variables in deployment.yaml
- name: Prepare Kubernetes manifests
  run: |
    # Install yq for YAML manipulation
    sudo wget -qO /usr/local/bin/yq https://github.com/mikefarah/yq/releases/latest/download/yq_linux_amd64
    sudo chmod +x /usr/local/bin/yq
    
    # Update the image name using yq (only in the Deployment, document 0)
    export IMAGE_NAME="ghcr.io/${{ env.REPO_LOWER }}/llmops-api:latest"
    yq eval-all '(select(di == 0) | .spec.template.spec.containers[0].image = strenv(IMAGE_NAME)) // .' -i llmops/Lab1-LLMOps-Pipeline/k8s/deployment.yaml
    
    echo "=== Updated deployment.yaml ==="
    cat llmops/Lab1-LLMOps-Pipeline/k8s/deployment.yaml
    echo ""
    echo "=== Verifying image name ==="
    yq eval 'select(di == 0) | .spec.template.spec.containers[0].image' llmops/Lab1-LLMOps-Pipeline/k8s/deployment.yaml
    echo "=== Verifying Service is intact ==="
    yq eval 'select(di == 1) | .kind' llmops/Lab1-LLMOps-Pipeline/k8s/deployment.yaml
```

### Key Points:

- ✅ **`eval-all`**: Processes all documents in the file
- ✅ **`select(di == 0)`**: Targets only document index 0 (Deployment)
- ✅ **`// .`**: Passes through all other documents unchanged
- ✅ **`strenv(IMAGE_NAME)`**: Safely uses environment variable
- ✅ **Verification**: Checks both Deployment image and Service integrity

### Why yq Instead of sed?

- ✅ **Safer**: Understands YAML structure, won't break formatting
- ✅ **More reliable**: No regex escaping issues with special characters
- ✅ **Verifiable**: Can easily query the updated value
- ✅ **Standard**: Widely used in CI/CD pipelines

## What Changed

**Before (broken):**
```yaml
image: ghcr.io/${{ github.repository }}/llmops-api:latest
```

**After (working):**
```yaml
image: ghcr.io/your-username/your-repo/llmops-api:latest
```

## Next Steps

1. **Commit the updated workflow:**
   ```bash
   git add .github/workflows/lab1-workflow.yml
   git commit -m "Fix image name substitution using yq"
   git push origin lab1
   ```

2. **Monitor the workflow** - The new step will show:
   - The complete updated deployment.yaml
   - The exact image name being used

3. **Verify** - Check the workflow output for:
   ```
   === Verifying image name ===
   ghcr.io/your-username/your-repo/llmops-api:latest
   ```

The deployment should now proceed without the InvalidImageName error!
