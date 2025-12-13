import os
import time
import requests
import pandas as pd
import mlflow
from datasets import Dataset
from ragas import evaluate
from ragas.metrics import faithfulness, answer_relevance
from langchain_openai import AzureChatOpenAI, AzureOpenAIEmbeddings

# Configuration
API_URL = "http://localhost:8080/v1/chat/completions"
MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")

# Azure Config for Ragas (Judges)
azure_deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o-mini")
azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
azure_key = os.getenv("AZURE_OPENAI_KEY")
api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")

# Initialize Azure LLM/Embeddings for Ragas
# Note: Ragas uses these to evaluate the quality of the answers
azure_llm = AzureChatOpenAI(
    deployment_name=azure_deployment,
    model_name=azure_deployment,
    openai_api_base=azure_endpoint,
    openai_api_version=api_version,
    openai_api_key=azure_key
)

azure_embeddings = AzureOpenAIEmbeddings(
    deployment=azure_deployment, # Often requires an embedding model deployment, falling back to same if works or needing separate config
    model=azure_deployment,
    azure_endpoint=azure_endpoint,
    openai_api_key=azure_key,
    openai_api_version=api_version
)

# Sample Data (Questions and Ground Truths context would ideally be retrieved)
# For this demo, we use simple Q&A where we provide 'context' manually or assume it's generated.
# Ragas Faithfulness requires 'contexts'. Answer Relevance requires 'question' and 'answer'.
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
    }
]

def generate_answers(data):
    """Generate answers from the running API"""
    results = []
    print(f"Generating answers for {len(data)} questions...")
    
    for item in data:
        try:
            payload = {
                "messages": [{"role": "user", "content": item["question"]}],
                "metadata": {"department": "test-eval"}
            }
            # Add a system prompt context if we want to simulate RAG, but here we just ask the model.
            # To test Faithfulness accurately, the model should ideally use the provided context.
            # Since our API is a general chatbot, we'll see how it performs.
            # We insert context into the message to simulate RAG for the generation step
            
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
    print("🚀 Starting Evaluation...")
    results = generate_answers(eval_data)
    
    if not results:
        print("❌ No results generated. Check API connection.")
        return

    # 2. Convert to Dataset
    dataset = Dataset.from_pandas(pd.DataFrame(results))
    
    # 3. Configure Ragas to use Azure
    # We pass the llm and embeddings explicitly
    
    # 4. Run Evaluation
    print("running ragas evaluation...")
    scores = evaluate(
        dataset,
        metrics=[faithfulness, answer_relevance],
        llm=azure_llm,
        embeddings=azure_embeddings
    )
    
    print(f"📊 Evaluation Scores: {scores}")

    # 5. Log to MLflow
    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    mlflow.set_experiment("llmops-ragas-evals")
    
    with mlflow.start_run(run_name=f"eval-{int(time.time())}"):
        # Log aggregate metrics
        mlflow.log_metrics(scores)
        
        # Log evaluation dataset as artifact
        df_scores = scores.to_pandas()
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
