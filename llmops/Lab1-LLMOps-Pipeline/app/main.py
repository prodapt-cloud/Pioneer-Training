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

# OpenTelemetry imports
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import Resource

# Initialize OpenTelemetry
OTEL_ENABLED = os.getenv("OTEL_ENABLED", "true").lower() == "true"
if OTEL_ENABLED:
    try:
        resource = Resource(attributes={
            "service.name": "llmops-api",
            "service.version": "1.0.0",
            "deployment.environment": os.getenv("ENVIRONMENT", "production")
        })
        
        provider = TracerProvider(resource=resource)
        
        # Add OTLP exporter if endpoint is configured
        otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
        if otlp_endpoint:
            otlp_exporter = OTLPSpanExporter(endpoint=otlp_endpoint)
            provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
        
        trace.set_tracer_provider(provider)
        tracer = trace.get_tracer(__name__)
        print(f"✅ OpenTelemetry tracing enabled")
    except Exception as e:
        print(f"⚠️  OpenTelemetry initialization failed: {e}")
        OTEL_ENABLED = False
        tracer = None
else:
    print("ℹ️  OpenTelemetry tracing disabled")
    tracer = None


# === CONFIG ===
r = redis.Redis(host=os.getenv("REDIS_HOST", "redis"), port=6379, db=0, decode_responses=True)
PROMPT_PATH = "/app/prompt/assistant_v1_openai.jinja2"  # OpenAI-compatible prompt

# Load prompt template
with open(PROMPT_PATH) as f:
    PROMPT_CONTENT = f.read()
    prompt_template = Template(PROMPT_CONTENT)

# === MLFLOW CONFIGURATION ===
MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
MLFLOW_ENABLED = os.getenv("MLFLOW_ENABLED", "true").lower() == "true"

if MLFLOW_ENABLED:
    try:
        mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
        
        # Set local artifact storage to avoid GCS anonymous credentials error
        os.environ["MLFLOW_ARTIFACT_ROOT"] = "/tmp/mlflow-artifacts"
        
        mlflow.set_experiment("llmops-production-api")
        print(f"✅ MLflow tracking enabled: {MLFLOW_TRACKING_URI}")
        print(f"   Artifact storage: /tmp/mlflow-artifacts")
    except Exception as e:
        print(f"⚠️  MLflow tracking disabled: {e}")
        MLFLOW_ENABLED = False
else:
    print("ℹ️  MLflow tracking disabled (MLFLOW_ENABLED=false)")



app = FastAPI(title="LLMOps Production API", version="1.0.0")

# === LLM CONFIGURATION ===
def get_llm_config():
    """
    Determine which LLM provider to use based on available credentials.
    Priority: Azure OpenAI > OpenAI > Error
    """
    print("=" * 60)
    print("🔍 LLM Configuration Debug")
    print("=" * 60)
    
    # Azure OpenAI configuration
    azure_key = os.getenv("AZURE_OPENAI_KEY")
    azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    azure_api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")
    azure_deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o-mini")
    
    # OpenAI configuration
    openai_key = os.getenv("OPENAI_API_KEY")
    
    # Debug: Show what's detected (masked)
    print(f"AZURE_OPENAI_KEY: {'SET (len=' + str(len(azure_key)) + ')' if azure_key else 'NOT SET'}")
    print(f"AZURE_OPENAI_ENDPOINT: {azure_endpoint if azure_endpoint else 'NOT SET'}")
    print(f"AZURE_OPENAI_API_VERSION: {azure_api_version}")
    print(f"AZURE_OPENAI_DEPLOYMENT_NAME: {azure_deployment}")
    print(f"OPENAI_API_KEY: {'SET (len=' + str(len(openai_key)) + ')' if openai_key else 'NOT SET'}")
    print("=" * 60)
    
    if azure_key and azure_endpoint:
        # Use Azure OpenAI
        print("✅ Selected: Azure OpenAI")
        return {
            "provider": "azure",
            "model": f"azure/{azure_deployment}",
            "api_key": azure_key,
            "api_base": azure_endpoint,
            "api_version": azure_api_version,
        }
    elif openai_key:
        # Use OpenAI
        print("✅ Selected: OpenAI")
        return {
            "provider": "openai",
            "model": "gpt-4o-mini",
            "api_key": openai_key,
        }
    else:
        # No credentials available
        print("❌ No LLM credentials found!")
        print("   Please set either:")
        print("   - OPENAI_API_KEY, OR")
        print("   - AZURE_OPENAI_KEY + AZURE_OPENAI_ENDPOINT")
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

# Instrument FastAPI with OpenTelemetry
if OTEL_ENABLED and tracer:
    try:
        FastAPIInstrumentor.instrument_app(app)
        print("✅ FastAPI instrumented with OpenTelemetry")
    except Exception as e:
        print(f"⚠️  FastAPI instrumentation failed: {e}")



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
    start_time = datetime.now()
    user_msg = request.messages[-1].content
    dept = request.metadata.get("department", "general")
    cache_hit = False
    
    # Get current trace context
    current_span = trace.get_current_span() if OTEL_ENABLED else None
    trace_id = None
    if current_span:
        trace_id = format(current_span.get_span_context().trace_id, '032x')

    # Start MLflow run if enabled
    mlflow_run = None
    if MLFLOW_ENABLED:
        try:
            mlflow_run = mlflow.start_run(run_name=f"chat-{start_time.strftime('%Y%m%d-%H%M%S')}")
            if trace_id:
                mlflow.log_param("trace_id", trace_id)
        except Exception as e:
            print(f"⚠️  Failed to start MLflow run: {e}")

    try:
        # Span for cache lookup
        with tracer.start_as_current_span("cache_lookup") if tracer else nullcontext():
            cache_key = get_cache_key([m.dict() for m in request.messages], dept)
            if cached := r.get(cache_key):
                print("Cache HIT")
                cache_hit = True
                resp_payload = json.loads(cached)
                
                if current_span:
                    current_span.set_attribute("cache.hit", True)
                
                # Log cache hit to MLflow
                if mlflow_run:
                    mlflow.log_param("cache_hit", True)
                    mlflow.log_param("department", dept)
                    mlflow.log_metric("response_time_ms", (datetime.now() - start_time).total_seconds() * 1000)
                
                return JSONResponse(content=resp_payload)

        # Span for prompt rendering
        with tracer.start_as_current_span("render_prompt") if tracer else nullcontext():
            rendered = prompt_template.render(
                current_date=datetime.now().strftime("%Y-%m-%d"),
                department=dept,
                user_question=user_msg
            )

        # Check if LLM is configured
        if LLM_CONFIG["provider"] == "none":
            if current_span:
                current_span.set_attribute("error", "LLM not configured")
            if mlflow_run:
                mlflow.log_param("error", "LLM not configured")
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
        
        # Log parameters to MLflow
        if mlflow_run:
            # Log LLM parameters
            mlflow.log_param("provider", LLM_CONFIG["provider"])
            mlflow.log_param("model", LLM_CONFIG["model"])
            mlflow.log_param("temperature", llm_params["temperature"])
            mlflow.log_param("max_tokens", llm_params["max_tokens"])
            mlflow.log_param("department", dept)
            mlflow.log_param("cache_hit", False)
            
            # Log Azure-specific params
            if LLM_CONFIG["provider"] == "azure":
                mlflow.log_param("api_version", llm_params["api_version"])
                mlflow.log_param("api_base", llm_params["api_base"])
            
            # Log prompt template (non-blocking)
            try:
                mlflow.log_text(PROMPT_CONTENT, "prompt_template.jinja2")
                mlflow.log_text(rendered, "rendered_prompt.txt")
                mlflow.log_text(user_msg, "user_message.txt")
            except Exception as e:
                print(f"⚠️  Failed to log artifacts to MLflow: {e}")
            
            # Log tags
            mlflow.set_tag("environment", "production")
            mlflow.set_tag("department", dept)
        
        # Span for LLM API call
        llm_start = datetime.now()
        with tracer.start_as_current_span("llm_completion") if tracer else nullcontext() as llm_span:
            if llm_span:
                llm_span.set_attribute("llm.provider", LLM_CONFIG["provider"])
                llm_span.set_attribute("llm.model", LLM_CONFIG["model"])
                llm_span.set_attribute("llm.temperature", llm_params["temperature"])
            
            response = litellm.completion(**llm_params)
        
        llm_duration = (datetime.now() - llm_start).total_seconds()

        answer = response.choices[0].message.content
        
        # Log response metrics to MLflow
        if mlflow_run:
            mlflow.log_metric("llm_latency_ms", llm_duration * 1000)
            mlflow.log_metric("total_response_time_ms", (datetime.now() - start_time).total_seconds() * 1000)
            mlflow.log_metric("prompt_tokens", response.usage.prompt_tokens if hasattr(response, 'usage') else 0)
            mlflow.log_metric("completion_tokens", response.usage.completion_tokens if hasattr(response, 'usage') else 0)
            mlflow.log_metric("total_tokens", response.usage.total_tokens if hasattr(response, 'usage') else 0)
            
            # Log response text (non-blocking)
            try:
                mlflow.log_text(answer, "response.txt")
            except Exception as e:
                print(f"⚠️  Failed to log response artifact: {e}")

        resp_payload = {
            "id": "chatcmpl-xyz",
            "object": "chat.completion",
            "created": int(datetime.now().timestamp()),
            "model": LLM_CONFIG["model"],
            "choices": [{"index": 0, "message": {"role": "assistant", "content": answer}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 200, "completion_tokens": 100, "total_tokens": 300}
        }

        r.setex(cache_key, 3600, json.dumps(resp_payload))
        return JSONResponse(content=resp_payload)
    
    except Exception as e:
        # Log error to MLflow and trace
        if current_span:
            current_span.set_attribute("error", True)
            current_span.set_attribute("error.message", str(e))
        if mlflow_run:
            mlflow.log_param("error", str(e))
            mlflow.log_metric("error_occurred", 1)
        raise
    
    finally:
        # End MLflow run
        if mlflow_run:
            mlflow.end_run()


# Helper for null context when tracing is disabled
from contextlib import nullcontext