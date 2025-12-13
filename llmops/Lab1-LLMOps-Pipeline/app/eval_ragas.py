import os
import time
import requests
import pandas as pd
import mlflow
from datasets import Dataset
from ragas import evaluate
from ragas.metrics import faithfulness, answer_relevancy
from langchain_openai import AzureChatOpenAI, AzureOpenAIEmbeddings

# Configuration
# Default to port 8000 (pod internal). Use 8080 if running locally with port-forward.
API_URL = os.getenv("API_URL", "http://localhost:8000/v1/chat/completions")
MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")

# Azure Config for Ragas (Judges)
azure_deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o-mini")
azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
azure_key = os.getenv("AZURE_OPENAI_KEY")
api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")

# Initialize Azure LLM/Embeddings for Ragas
# Note: Ragas uses these to evaluate the quality of the answers
if not (azure_endpoint and azure_key):
    print("❌ Azure credentials not found. Please set AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_KEY.")
    exit(1)

azure_llm = AzureChatOpenAI(
    deployment_name=azure_deployment,
    model_name=azure_deployment,
    azure_endpoint=azure_endpoint,
    openai_api_version=api_version,
    openai_api_key=azure_key
)

from langchain_huggingface import HuggingFaceEmbeddings
from ragas.embeddings import LangchainEmbeddingsWrapper

# ... (API Keys setup remains for LLM)

# Initialize Local Embeddings (Cost-free)
# Using all-MiniLM-L6-v2 which is standard for lightweight eval
print("📥 Loading local embeddings (all-MiniLM-L6-v2)...")
hf_embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
azure_embeddings = LangchainEmbeddingsWrapper(hf_embeddings)

# Sample Data (Questions and Ground Truths context would ideally be retrieved)
eval_data = [
    {
        "question": "What is the capital of France?",
        "contexts": ["Paris is the capital and most populous city of France."],
        "ground_truth": "Paris"
    },
    {
        "question": "What does LLMOps stand for?",
        "contexts": ["LLMOps stands for Large Language Model Operations. It involves the practices and tools for managing the lifecycle of LLM-powered applications."],
        "ground_truth": "Large Language Model Operations"
    },
    {
        "question": "Explain the concept of RAG.",
        "contexts": ["Retrieval-Augmented Generation (RAG) is the process of optimizing the output of a large language model, so it references an authoritative knowledge base outside its training data sources before generating a response."],
        "ground_truth": "RAG (Retrieval-Augmented Generation) optimizes LLM output by referencing an external knowledge base."
    }
]

def generate_answers(data):
    """Generate answers from the running API"""
    results = []
    print(f"Generating answers for {len(data)} questions using {API_URL}...")
    
    for item in data:
        try:
            payload = {
                "messages": [{"role": "user", "content": item["question"]}],
                "metadata": {"department": "eval-ragas"}
            }
            # Inject context into prompt to "simulate" RAG for the generation, 
            # so the model has a chance to be faithful to the context.
            prompt_with_context = f"Context: {item['contexts'][0]}\n\nQuestion: {item['question']}"
            payload["messages"][0]["content"] = prompt_with_context

            response = requests.post(API_URL, json=payload)
            if response.status_code == 200:
                answer = response.json()["choices"][0]["message"]["content"]
                results.append({
                    "question": item["question"],
                    "answer": answer,
                    "contexts": item["contexts"],
                    "ground_truth": item["ground_truth"]
                })
            else:
                print(f"Error for {item['question']}: {response.text}")
        except Exception as e:
            print(f"Exception for {item['question']}: {e}")
            
    return results

def run_evaluation():
    # 1. Generate Answers
    print("🚀 Starting Ragas Evaluation...")
    results = generate_answers(eval_data)
    
    if not results:
        print("❌ No results generated. Check API connection.")
        return

    # 2. Convert to Dataset
    dataset = Dataset.from_pandas(pd.DataFrame(results))
    
    # 3. Run Evaluation
    print("🧠 Running Ragas metrics (Faithfulness, Answer Relevance)...")
    try:
        scores = evaluate(
            dataset,
            metrics=[faithfulness, answer_relevancy],
            llm=azure_llm,
            embeddings=azure_embeddings
        )
        print(f"📊 Evaluation Scores: {scores}")
    except Exception as e:
        print(f"❌ Ragas evaluation failed: {e}")
        return

    # 4. Log to MLflow
    if MLFLOW_TRACKING_URI:
        print(f"📝 Logging to MLflow: {MLFLOW_TRACKING_URI}")
        mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
        mlflow.set_experiment("llmops-ragas-evals")
        
        with mlflow.start_run(run_name=f"eval-{int(time.time())}"):
            # Log aggregate metrics via Pandas mean
            # (EvaluationResult not directly dict-convertible in this version)
            df_scores = scores.to_pandas()
            metrics = df_scores.select_dtypes(include="number").mean().to_dict()
            mlflow.log_metrics(metrics)
            
            # Log evaluation dataset as artifact
            csv_path = "eval_results.csv"
            df_scores.to_csv(csv_path, index=False)
            mlflow.log_artifact(csv_path)
            
            # Log configuration
            mlflow.log_param("eval_count", len(results))
            mlflow.log_param("eval_model", azure_deployment)
            
            print(f"✅ Results logged to MLflow experiment 'llmops-ragas-evals'")
            
            # Clean up
            if os.path.exists(csv_path):
                os.remove(csv_path)

if __name__ == "__main__":
    run_evaluation()
