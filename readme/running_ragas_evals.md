# 📊 Running Ragas Evaluations

I've added a Ragas evaluation script to your application! This script assesses your LLM's performance using metrics like **Faithfulness** and **Answer Relevance** and logs the results to MLflow.

## 📍 Script Location
`app/eval_ragas.py` (Deployed with your application)

---

## 🚀 Option 1: Run Inside Pod (Recommended)

The easiest way is to run it inside the running API pod, where all environment variables (Azure keys) and dependencies are already set.

### 1. Execute the script
```bash
# Get pod name
POD=$(kubectl get pods -l app=llmops-api -o jsonpath='{.items[0].metadata.name}')

# Run evaluation
kubectl exec -it $POD -- python eval_ragas.py
```

### 2. View Results
- **Console**: You'll see "Evaluation Scores" printed.
- **MLflow**: Check the `llmops-ragas-evals` experiment in your MLflow UI.

---

## 💻 Option 2: Run Locally

If you want to run it from your local machine:

1. **Install dependencies**:
   ```bash
   pip install ragas datasets langchain-openai pandas mlflow
   ```

2. **Set Environment Variables**:
   You need to set `AZURE_OPENAI_KEY`, `AZURE_OPENAI_ENDPOINT`, etc.
   ```bash
   # Example (PowerShell)
   $env:AZURE_OPENAI_KEY="your-key"
   $env:AZURE_OPENAI_ENDPOINT="https://your-endpoint.openai.azure.com"
   $env:AZURE_OPENAI_DEPLOYMENT_NAME="gpt-4o-mini"
   ```

3. **Port Forward API**:
   ```bash
   kubectl port-forward svc/llmops-service 8080:80
   ```

4. **Run Script**:
   ```bash
   # Tell script to use localhost:8080
   $env:API_URL="http://localhost:8080/v1/chat/completions"
   python app/eval_ragas.py
   ```

---

## 📈 Metrics Explained

- **Faithfulness**: How factually consistent the answer is with the provided context.
- **Answer Relevance**: How relevant the answer is to the question.

The script runs on a small sample dataset. You can extend `eval_data` in `app/eval_ragas.py` with your own test cases!
