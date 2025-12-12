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
        return {"status": "healthy", "redis": "connected"}
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

    response = litellm.completion(
        model="ollama/llama3.2:3b",
        messages=[{"role": "user", "content": rendered}],
        temperature=0.3,
        max_tokens=512
    )

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