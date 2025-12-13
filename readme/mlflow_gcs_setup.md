# MLflow with GCS Setup Guide

## 🎯 Overview

To use MLflow with Google Cloud Storage for artifact storage, you need:
1. GCS bucket for artifacts
2. Service account with GCS permissions
3. Credentials configured in Kubernetes
4. MLflow server configured to use GCS

---

## 📦 Step 1: Create GCS Bucket

```bash
# Set variables
PROJECT_ID="your-gcp-project-id"
BUCKET_NAME="mlflow-artifacts-${PROJECT_ID}"
REGION="us-central1"

# Create bucket
gcloud storage buckets create gs://${BUCKET_NAME} \
  --project=${PROJECT_ID} \
  --location=${REGION}
```

---

## 🔐 Step 2: Create Service Account

```bash
# Create service account
gcloud iam service-accounts create mlflow-sa \
  --display-name="MLflow Service Account" \
  --project=${PROJECT_ID}

# Grant storage permissions
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
  --member="serviceAccount:mlflow-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/storage.objectAdmin"

# Create and download key
gcloud iam service-accounts keys create mlflow-sa-key.json \
  --iam-account=mlflow-sa@${PROJECT_ID}.iam.gserviceaccount.com
```

---

## 🔧 Step 3: Add Credentials to Kubernetes

### Option A: Using Kubernetes Secret

```bash
# Create secret from service account key
kubectl create secret generic gcs-credentials \
  --from-file=key.json=mlflow-sa-key.json

# Delete local key file (security)
rm mlflow-sa-key.json
```

### Option B: Using GitHub Secret (for CI/CD)

1. Base64 encode the key:
   ```bash
   cat mlflow-sa-key.json | base64 -w 0
   ```

2. Add to GitHub Secrets:
   - Name: `GCS_SERVICE_ACCOUNT_KEY`
   - Value: The base64 encoded string

3. Update workflow to create secret:
   ```yaml
   - name: Create GCS credentials
     run: |
       echo "${{ secrets.GCS_SERVICE_ACCOUNT_KEY }}" | base64 -d > /tmp/gcs-key.json
       kubectl create secret generic gcs-credentials \
         --from-file=key.json=/tmp/gcs-key.json \
         --dry-run=client -o yaml | kubectl apply -f -
       rm /tmp/gcs-key.json
   ```

---

## 📝 Step 4: Update Deployment

Update [`deployment.yaml`](file:///d:/Workspace/pioneer/Pioneer-Training/llmops/Lab1-LLMOps-Pipeline/k8s/deployment.yaml):

```yaml
spec:
  containers:
  - name: llmops-api
    env:
    # ... existing env vars ...
    
    # GCS configuration
    - name: GOOGLE_APPLICATION_CREDENTIALS
      value: /var/secrets/google/key.json
    - name: MLFLOW_ARTIFACT_ROOT
      value: gs://mlflow-artifacts-your-project/artifacts
    
    volumeMounts:
    - name: gcs-credentials
      mountPath: /var/secrets/google
      readOnly: true
  
  volumes:
  - name: gcs-credentials
    secret:
      secretName: gcs-credentials
```

---

## 🚀 Step 5: Update Application Code

Update [`main.py`](file:///d:/Workspace/pioneer/Pioneer-Training/llmops/Lab1-LLMOps-Pipeline/app/main.py):

```python
# === MLFLOW CONFIGURATION ===
MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
MLFLOW_ARTIFACT_ROOT = os.getenv("MLFLOW_ARTIFACT_ROOT", "/tmp/mlflow-artifacts")
MLFLOW_ENABLED = os.getenv("MLFLOW_ENABLED", "true").lower() == "true"

if MLFLOW_ENABLED:
    try:
        mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
        
        # Set artifact storage (GCS or local)
        if MLFLOW_ARTIFACT_ROOT.startswith("gs://"):
            print(f"✅ MLflow using GCS: {MLFLOW_ARTIFACT_ROOT}")
        else:
            os.environ["MLFLOW_ARTIFACT_ROOT"] = MLFLOW_ARTIFACT_ROOT
            print(f"✅ MLflow using local storage: {MLFLOW_ARTIFACT_ROOT}")
        
        mlflow.set_experiment("llmops-production-api")
        print(f"✅ MLflow tracking enabled: {MLFLOW_TRACKING_URI}")
    except Exception as e:
        print(f"⚠️  MLflow tracking disabled: {e}")
        MLFLOW_ENABLED = False
```

---

## 🖥️ Step 6: Deploy MLflow Server (Optional)

If you want to run MLflow server with GCS backend:

```yaml
# k8s/mlflow-server.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mlflow-server
spec:
  replicas: 1
  selector:
    matchLabels:
      app: mlflow-server
  template:
    metadata:
      labels:
        app: mlflow-server
    spec:
      containers:
      - name: mlflow
        image: ghcr.io/mlflow/mlflow:latest
        command:
        - mlflow
        - server
        - --host=0.0.0.0
        - --port=5000
        - --backend-store-uri=sqlite:///mlflow/mlflow.db
        - --default-artifact-root=gs://mlflow-artifacts-your-project/artifacts
        env:
        - name: GOOGLE_APPLICATION_CREDENTIALS
          value: /var/secrets/google/key.json
        volumeMounts:
        - name: gcs-credentials
          mountPath: /var/secrets/google
          readOnly: true
        - name: mlflow-data
          mountPath: /mlflow
        ports:
        - containerPort: 5000
      volumes:
      - name: gcs-credentials
        secret:
          secretName: gcs-credentials
      - name: mlflow-data
        emptyDir: {}
---
apiVersion: v1
kind: Service
metadata:
  name: mlflow-service
spec:
  type: LoadBalancer
  ports:
  - port: 5000
    targetPort: 5000
  selector:
    app: mlflow-server
```

---

## ✅ Verification

### Test GCS Access

```bash
# Exec into pod
POD=$(kubectl get pods -l app=llmops-api -o jsonpath='{.items[0].metadata.name}')
kubectl exec -it $POD -- bash

# Inside pod, test GCS access
python3 << EOF
from google.cloud import storage
client = storage.Client()
buckets = list(client.list_buckets())
print(f"✅ GCS access working! Found {len(buckets)} buckets")
EOF
```

### Check MLflow Artifacts

```python
import mlflow

mlflow.set_tracking_uri("http://mlflow-service:5000")
client = mlflow.tracking.MlflowClient()

# Get latest run
experiment = client.get_experiment_by_name("llmops-production-api")
runs = client.search_runs(experiment.experiment_id, max_results=1)

if runs:
    run_id = runs[0].info.run_id
    artifacts = client.list_artifacts(run_id)
    print(f"✅ Artifacts in GCS:")
    for artifact in artifacts:
        print(f"  - {artifact.path}")
```

---

## 💰 Cost Considerations

**GCS Pricing** (us-central1):
- Storage: $0.020 per GB/month
- Class A operations: $0.05 per 10,000 operations
- Class B operations: $0.004 per 10,000 operations

**Estimated monthly cost** (for small project):
- 10 GB storage: $0.20
- 100K operations: $0.50
- **Total: ~$0.70/month**

---

## 🔒 Security Best Practices

1. **Least Privilege**: Only grant `roles/storage.objectAdmin` on the specific bucket
2. **Rotate Keys**: Rotate service account keys regularly
3. **Use Workload Identity**: For GKE, use Workload Identity instead of service account keys
4. **Encrypt at Rest**: Enable encryption on GCS bucket
5. **Access Logs**: Enable GCS access logging for audit

---

## 🚨 Troubleshooting

### Error: "Anonymous credentials cannot be refreshed"

**Cause**: GCS credentials not configured

**Fix**:
1. Verify secret exists: `kubectl get secret gcs-credentials`
2. Check volume mount in pod
3. Verify `GOOGLE_APPLICATION_CREDENTIALS` env var

### Error: "Permission denied"

**Cause**: Service account lacks permissions

**Fix**:
```bash
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
  --member="serviceAccount:mlflow-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/storage.objectAdmin"
```

---

## ✨ Summary

**To use GCS with MLflow**:
1. ✅ Create GCS bucket
2. ✅ Create service account with storage permissions
3. ✅ Add credentials to Kubernetes secret
4. ✅ Mount secret in deployment
5. ✅ Set `GOOGLE_APPLICATION_CREDENTIALS` and `MLFLOW_ARTIFACT_ROOT`
6. ✅ Deploy and verify

**Current Setup**: Using local storage (`/tmp/mlflow-artifacts`)  
**To Switch to GCS**: Follow steps above and update `MLFLOW_ARTIFACT_ROOT` env var
