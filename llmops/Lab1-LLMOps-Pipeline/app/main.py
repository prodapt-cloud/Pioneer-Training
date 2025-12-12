# app/main.py
import os
import json
import hashlib
from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Dict, Any
from jinja2 import Template
import litellm
import redis
import mlflow

# === CONFIG ===
r = redis.Redis(host=os.getenv("REDIS_HOST", "redis"), port=6379, db=0, decode_responses=True)
PROMPT_PATH = "/app/prompt/assistant_v1.jinja2"

# Load prompt template
with open(PROMPT_PATH) as f:
    prompt_template = Template(f.read())

app = FastAPI(title="LLMOps Production API", version="1.0.0")

# === LLM CONFIGURATION ===
def get_llm_config():
    """
    Determine which LLM provider to use based on available credentials.
    Priority: Azure OpenAI > OpenAI > Error
    """
    # Azure OpenAI configuration
    azure_key = os.getenv("AZURE_OPENAI_KEY")
    azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    azure_api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")
    azure_deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o-mini")
    
    # OpenAI configuration
    openai_key = os.getenv("OPENAI_API_KEY")
    
    if azure_key and azure_endpoint:
        # Use Azure OpenAI
        return {
            "provider": "azure",
            "model": f"azure/{azure_deployment}",
            "api_key": azure_key,
            "api_base": azure_endpoint,
            "api_version": azure_api_version,
        }
    elif openai_key:
        # Use OpenAI
        return {
            "provider": "openai",
            "model": "gpt-4o-mini",
            "api_key": openai_key,
        }
    else:
        # No credentials available
        return {
            "provider": "none",
            "error": "No LLM credentials configured. Set OPENAI_API_KEY or AZURE_OPENAI_KEY + AZURE_OPENAI_ENDPOINT"
        }

# Initialize LLM config at startup
LLM_CONFIG = get_llm_config()
print(f"🤖 LLM Provider: {LLM_CONFIG.get('provider', 'unknown')}")
if LLM_CONFIG["provider"] == "azure":
    print(f"   Model: {LLM_CONFIG['model']}")
    print(f"   Endpoint: {LLM_CONFIG['api_base']}")
    print(f"   API Version: {LLM_CONFIG['api_version']}")
elif LLM_CONFIG["provider"] == "openai":
    print(f"   Model: {LLM_CONFIG['model']}")
else:
    print(f"   ⚠️  {LLM_CONFIG.get('error', 'Unknown error')}")


class ChatMessage(BaseModel):
    role: str
    content: str

class ChatCompletionRequest(BaseModel):
    model: str = "llama3.2"
    messages: List[ChatMessage]
    temperature: float = 0.3
    metadata: Dict[str, Any] = {}

def get_cache_key(messages: List[Dict], department: str) -> str:
    content = json.dumps(messages) + department
    return "cache:" + hashlib.sha256(content.encode()).hexdigest()

@app.get("/health")
async def health_check():
    """Health check endpoint for Kubernetes probes"""
    try:
        # Check Redis connection
        r.ping()
        health_data = {
            "status": "healthy",
            "redis": "connected",
            "llm_provider": LLM_CONFIG.get("provider", "unknown"),
        }
        
        # Add LLM model info if configured
        if LLM_CONFIG["provider"] != "none":
            health_data["llm_model"] = LLM_CONFIG.get("model", "unknown")
        
        return health_data
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "error": str(e)}
        )

@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "LLMOps Production API", "version": "1.0.0"}


@app.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest):
    user_msg = request.messages[-1].content
    dept = request.metadata.get("department", "general")

    cache_key = get_cache_key([m.dict() for m in request.messages], dept)
    if cached := r.get(cache_key):
        print("Cache HIT")
        return JSONResponse(content=json.loads(cached))

    rendered = prompt_template.render(
        current_date=datetime.now().strftime("%Y-%m-%d"),
        department=dept,
        user_question=user_msg
    )

    # Check if LLM is configured
    if LLM_CONFIG["provider"] == "none":
        return JSONResponse(
            status_code=503,
            content={
                "error": "LLM not configured",
                "message": LLM_CONFIG.get("error", "No LLM credentials available")
            }
        )

    # Call LLM with appropriate configuration
    llm_params = {
        "model": LLM_CONFIG["model"],
        "messages": [{"role": "user", "content": rendered}],
        "temperature": 0.3,
        "max_tokens": 512,
        "api_key": LLM_CONFIG["api_key"],
    }
    
    # Add Azure-specific parameters if using Azure
    if LLM_CONFIG["provider"] == "azure":
        llm_params["api_base"] = LLM_CONFIG["api_base"]
        llm_params["api_version"] = LLM_CONFIG["api_version"]
    
    response = litellm.completion(**llm_params)

    answer = response.choices[0].message.content

    resp_payload = {
        "id": "chatcmpl-xyz",
        "object": "chat.completion",
        "created": int(datetime.now().timestamp()),
        "model": "llama3.2-local",
        "choices": [{"index": 0, "message": {"role": "assistant", "content": answer}, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 200, "completion_tokens": 100, "total_tokens": 300}
    }

    r.setex(cache_key, 3600, json.dumps(resp_payload))
    return JSONResponse(content=resp_payload)