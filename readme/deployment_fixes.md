# Kubernetes Deployment Timeout - Root Causes & Fixes

## Problem Summary

The deployment was timing out with the error:
```
Waiting for deployment "llmops-api" rollout to finish: 0 of 2 updated replicas are available...
error: timed out waiting for the condition
```

## Root Causes Identified

### 1. **Template Variable Not Substituted**
- **Issue**: The `deployment.yaml` contained `${{ github.repository }}` which is a GitHub Actions template variable
- **Impact**: Kubernetes tried to pull an image with a literal `${{ github.repository }}` in the name, which doesn't exist
- **Fix**: Added a workflow step using `yq` (YAML processor) to safely update the image name with the actual repository name
- **Why yq**: More reliable than `sed` for structured YAML data, prevents parsing errors

### 2. **Missing Redis Dependency**
- **Issue**: The application requires Redis for caching, but no Redis deployment existed
- **Impact**: The app would fail health checks because it couldn't connect to Redis
- **Fix**: Created `redis.yaml` with Redis deployment and service

### 3. **No Health Check Endpoint**
- **Issue**: The FastAPI app didn't have a `/health` endpoint
- **Impact**: Kubernetes readiness/liveness probes would fail
- **Fix**: Added `/health` endpoint to `main.py` that checks Redis connectivity

### 4. **Wrong Prompt File Path**
- **Issue**: Code referenced `/app/prompts/` but actual directory is `/app/prompt/`
- **Impact**: Application would crash on startup when trying to load the template
- **Fix**: Corrected the path in `main.py`

### 5. **Wrong Redis Host**
- **Issue**: Redis host was set to `localhost` by default
- **Impact**: In Kubernetes, the app needs to connect to the `redis` service, not localhost
- **Fix**: Changed default Redis host from `localhost` to `redis`

### 6. **Missing Image Pull Secrets**
- **Issue**: No credentials configured to pull images from GitHub Container Registry (GHCR)
- **Impact**: Kubernetes couldn't pull the private Docker image
- **Fix**: Added image pull secret creation step and referenced it in deployment

### 7. **Deployment Order**
- **Issue**: All resources were applied at once without ensuring dependencies were ready
- **Impact**: API pods might start before Redis is available
- **Fix**: Deploy Redis first, wait for it to be ready, then deploy the API

## Changes Made

### 1. [deployment.yaml](file:///d:/Workspace/pioneer/Pioneer-Training/llmops/Lab1-LLMOps-Pipeline/k8s/deployment.yaml)
- ✅ Added `imagePullPolicy: Always`
- ✅ Added `imagePullSecrets` reference
- ✅ Added readiness probe (`/health` endpoint)
- ✅ Added liveness probe (`/health` endpoint)
- ✅ Added `PORT` environment variable
- ✅ Increased timeout from 180s to 300s

### 2. [redis.yaml](file:///d:/Workspace/pioneer/Pioneer-Training/llmops/Lab1-LLMOps-Pipeline/k8s/redis.yaml) (NEW)
- ✅ Created Redis deployment with 1 replica
- ✅ Added Redis service (ClusterIP)
- ✅ Added health checks for Redis
- ✅ Set appropriate resource limits

### 3. [main.py](file:///d:/Workspace/pioneer/Pioneer-Training/llmops/Lab1-LLMOps-Pipeline/app/main.py)
- ✅ Added `/health` endpoint with Redis connectivity check
- ✅ Added `/` root endpoint
- ✅ Fixed Redis host from `localhost` to `redis`
- ✅ Fixed prompt path from `/app/prompts/` to `/app/prompt/`

### 4. [lab1-workflow.yml](file:///d:/Workspace/pioneer/Pioneer-Training/.github/workflows/lab1-workflow.yml)
- ✅ Added step to substitute `${{ github.repository }}` variable
- ✅ Added image pull secret creation
- ✅ Split deployment into Redis first, then API
- ✅ Added debug step that runs on failure
- ✅ Increased deployment timeout to 300s

## Next Steps

### To Test the Fixes:

1. **Commit and push your changes** to the `lab1` branch:
   ```bash
   git add .
   git commit -m "Fix Kubernetes deployment timeout issues"
   git push origin lab1
   ```

2. **Monitor the GitHub Actions workflow**:
   - Go to your repository on GitHub
   - Click on "Actions" tab
   - Watch the "Deploy LLMOps Endpoint" workflow run

3. **If it still fails**, the debug step will now show:
   - Deployment status
   - Pod status with details
   - Pod descriptions (showing events)
   - Pod logs (last 100 lines)

### Common Issues to Watch For:

1. **Image Pull Errors**: Check if the image was built and pushed successfully
2. **Redis Connection**: Verify Redis pod is running before API pods start
3. **Resource Constraints**: The Kind cluster might not have enough resources for the requested CPU/memory
4. **Application Errors**: Check pod logs for Python errors or missing dependencies

## Verification Commands

If you have `kubectl` access to the cluster, you can run:

```bash
# Check all resources
kubectl get all

# Check pod status
kubectl get pods -o wide

# Describe the deployment
kubectl describe deployment llmops-api

# Check pod logs
kubectl logs -l app=llmops-api --tail=50

# Check Redis
kubectl get pods -l app=redis
kubectl logs -l app=redis --tail=20

# Test the health endpoint
kubectl port-forward svc/llmops-service 8080:80
curl http://localhost:8080/health
```

## Architecture Overview

```
┌─────────────────────────────────────────┐
│         LoadBalancer Service            │
│         (llmops-service:80)             │
└────────────────┬────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────┐
│      LLMOps API Deployment (2 pods)     │
│                                         │
│  ┌─────────────┐    ┌─────────────┐   │
│  │   Pod 1     │    │   Pod 2     │   │
│  │  :8000      │    │  :8000      │   │
│  └──────┬──────┘    └──────┬──────┘   │
│         │                  │           │
│         └────────┬─────────┘           │
└──────────────────┼─────────────────────┘
                   │
                   ▼
         ┌─────────────────┐
         │  Redis Service  │
         │  (redis:6379)   │
         └────────┬────────┘
                  │
                  ▼
         ┌─────────────────┐
         │  Redis Pod      │
         │  (cache)        │
         └─────────────────┘
```

## Summary

All identified issues have been fixed. The deployment should now:
1. ✅ Pull the correct Docker image from GHCR
2. ✅ Start Redis before the API
3. ✅ Pass health checks
4. ✅ Successfully connect to Redis
5. ✅ Load the prompt template correctly
6. ✅ Provide detailed debug information if it fails

Push your changes and re-run the workflow to verify the fixes!
