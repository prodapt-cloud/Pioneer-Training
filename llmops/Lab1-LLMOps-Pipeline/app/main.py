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
from openai import AzureOpenAI
import redis
import mlflow
import httpx

# OpenTelemetry imports
from opentelemetry import trace
from phoenix.otel import register
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from openinference.instrumentation.openai import OpenAIInstrumentor

# Initialize OpenTelemetry via Phoenix
OTEL_ENABLED = os.getenv("OTEL_ENABLED", "true").lower() == "true"
if OTEL_ENABLED:
    try:
        # Register Phoenix as the tracer provider
        # This automatically sets up the OTLP exporter to the endpoint
        tracer_provider = register(
            project_name="llmops-api",
            endpoint=os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://127.0.0.1:6006"),
            set_global_tracer_provider=True
        )
        
        # Auto-instrument OpenAI client for Phoenix
        OpenAIInstrumentor(tracer_provider=tracer_provider).instrument()
        
        trace.set_tracer_provider(tracer_provider)
        tracer = trace.get_tracer(__name__)
        
        print(f"✅ OpenTelemetry tracing enabled (Phoenix/OTLP)")
    except Exception as e:
        print(f"⚠️  OpenTelemetry initialization failed: {e}")
        OTEL_ENABLED = False
        tracer = None
else:
    print("ℹ️  OpenTelemetry tracing disabled")
    tracer = None


# === CONFIG ===
REDIS_ENABLED = os.getenv("REDIS_ENABLED", "true").lower() == "true"
REDIS_HOST = os.getenv("REDIS_HOST", "redis")

class MockRedis:
    def get(self, key): return None
    def setex(self, key, time, value): pass
    def ping(self): return True

if REDIS_ENABLED:
    try:
        r = redis.Redis(host=REDIS_HOST, port=6379, db=0, decode_responses=True, socket_timeout=5)
        r.ping() # Fail fast if not reachable
        print(f"✅ Redis connected: {REDIS_HOST}")
    except Exception as e:
        print(f"⚠️  Redis connection failed: {e}")
        print("   Caching disabled")
        r = MockRedis()
else:
    print("ℹ️  Redis disabled (REDIS_ENABLED=false)")
    r = MockRedis()

# Use relative path for prompts to ensure it works in both container and local env
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROMPT_PATH = os.path.join(BASE_DIR, "prompt", "assistant_v1_openai.jinja2")

# Load prompt template
with open(PROMPT_PATH) as f:
    PROMPT_CONTENT = f.read()
    prompt_template = Template(PROMPT_CONTENT)

# === MLFLOW CONFIGURATION ===
MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
MLFLOW_ENABLED = os.getenv("MLFLOW_ENABLED", "true").lower() == "true"

if MLFLOW_ENABLED:
    try:
        # Check connection first by setting URI
        os.environ["MLFLOW_HTTP_REQUEST_TIMEOUT"] = "5" # Fail fast (5s) if server is down
        mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
        
        # Set local artifact storage to avoid GCS anonymous credentials error
        os.environ["MLFLOW_ARTIFACT_ROOT"] = "/tmp/mlflow-artifacts"
        
        mlflow.set_experiment("llmops-production-api")
        mlflow.openai.autolog()
        print(f"✅ MLflow tracking enabled: {MLFLOW_TRACKING_URI}")
        print(f"   Artifact storage: /tmp/mlflow-artifacts")
    except Exception as e:
        print(f"⚠️  MLflow tracking disabled: {e}")
        MLFLOW_ENABLED = False
else:
    print("ℹ️  MLflow tracking disabled (MLFLOW_ENABLED=false)")



app = FastAPI(title="LLMOps Production API", version="1.0.0")

SENSITIVE = {"authorization", "api-key"}

def log_request(request: httpx.Request):
    safe = {}
    for k, v in request.headers.items():
        if k.lower() in SENSITIVE:
            safe[k] = f"<redacted len={len(v)} repr_tail={repr(v[-10:])}>"
        else:
            safe[k] = f"<len={len(v)} repr={repr(v)}>"
    print("OUTGOING HEADERS:", safe)

def log_response(response: httpx.Response):
    print("STATUS:", response.status_code)

http_client = httpx.Client(event_hooks={"request": [log_request], "response": [log_response]})

# === LLM CONFIGURATION ===
def get_llm_config():
    """
    Initialize Azure OpenAI client based on environment variables.
    Returns: (client, deployment_name, provider) or (None, None, "none")
    """
    print("=" * 60)
    print("🔍 LLM Configuration Debug")
    print("=" * 60)
    
    # Azure OpenAI configuration
    azure_key = os.getenv("AZURE_OPENAI_KEY")
    azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    azure_api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")
    azure_deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4.1-mini")
    
    # Debug: Show what's detected (masked)
    print(f"AZURE_OPENAI_KEY: {'SET (len=' + str(len(azure_key)) + ')' if azure_key else 'NOT SET'}")
    print(f"AZURE_OPENAI_ENDPOINT: {azure_endpoint if azure_endpoint else 'NOT SET'}")
    print(f"AZURE_OPENAI_API_VERSION: {azure_api_version}")
    print(f"AZURE_OPENAI_DEPLOYMENT_NAME: {azure_deployment}")
    print("=" * 60)
    
    if azure_key and azure_endpoint:
        # Initialize Azure OpenAI client
        print("✅ Initializing Azure OpenAI client")
        try:
            client = AzureOpenAI(
                api_key=azure_key.strip(),
                api_version=azure_api_version,
                azure_endpoint=azure_endpoint.strip(),
                http_client=http_client
            )
            print(f"✅ Azure OpenAI client initialized successfully")
            print(f"   Endpoint: {azure_endpoint}")
            print(f"   Deployment: {azure_deployment}")
            return client, azure_deployment, "azure"
        except Exception as e:
            print(f"❌ Failed to initialize Azure OpenAI client: {e}")
            return None, None, "none"
    else:
        # No credentials available
        print("❌ No Azure OpenAI credentials found!")
        print("   Please set:")
        print("   - AZURE_OPENAI_KEY")
        print("   - AZURE_OPENAI_ENDPOINT")
        return None, None, "none"

# Initialize LLM client at startup
AZURE_CLIENT, AZURE_DEPLOYMENT, LLM_PROVIDER = get_llm_config()

print(f"🤖 LLM Provider: {LLM_PROVIDER}")
if LLM_PROVIDER == "azure":
    print(f"   Deployment: {AZURE_DEPLOYMENT}")
    print(f"   Ready to serve requests")
else:
    print(f"   ⚠️  No LLM configured - API will return 503")

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
            "llm_provider": LLM_PROVIDER,
        }
        
        # Add LLM model info if configured
        if LLM_PROVIDER != "none":
            health_data["llm_model"] = AZURE_DEPLOYMENT
        
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
        if LLM_PROVIDER == "none" or not AZURE_CLIENT:
            if current_span:
                current_span.set_attribute("error", "LLM not configured")
            if mlflow_run:
                mlflow.log_param("error", "LLM not configured")
            return JSONResponse(
                status_code=503,
                content={
                    "error": "LLM not configured",
                    "message": "No Azure OpenAI credentials available. Please configure AZURE_OPENAI_KEY and AZURE_OPENAI_ENDPOINT."
                }
            )

        # Log parameters to MLflow
        if mlflow_run:
            # Log LLM parameters
            mlflow.log_param("provider", "azure")
            mlflow.log_param("model", AZURE_DEPLOYMENT)
            mlflow.log_param("temperature", 0.3)
            mlflow.log_param("max_tokens", 512)
            mlflow.log_param("department", dept)
            mlflow.log_param("cache_hit", False)
            
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
                llm_span.set_attribute("llm.provider", "azure")
                llm_span.set_attribute("llm.model", AZURE_DEPLOYMENT)
                llm_span.set_attribute("llm.temperature", 0.3)
            
            # Use native Azure OpenAI client
            response = None
            try:
                # az_client= AzureOpenAI(
                #     api_key=AZURE_OPENAI_KEY,
                #     api_base=AZURE_OPENAI_ENDPOINT,
                #     api_version=AZURE_OPENAI_API_VERSION,
                #     http_client=http_client
                # )
                # response = az_client.chat.completions.create(
                #     model=AZURE_DEPLOYMENT,
                #     messages=[{"role": "user", "content": rendered}],
                #     temperature=0.3,
                #     max_tokens=512,
                # )

                # Use native Azure OpenAI client
                response = AZURE_CLIENT.chat.completions.create(
                  model=AZURE_DEPLOYMENT,
                  messages=[{"role": "user", "content": rendered}],
                  temperature=0.3,
                  max_tokens=512
                )  

            except Exception as e:
                print(f"Error: {e}")
                raise e
        
        llm_duration = (datetime.now() - llm_start).total_seconds()

        if not response or not response.choices:
            raise Exception("Received empty or invalid response from LLM provider")

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
            "id": response.id,
            "object": "chat.completion",
            "created": response.created,
            "model": response.model,
            "choices": [{"index": 0, "message": {"role": "assistant", "content": answer}, "finish_reason": response.choices[0].finish_reason}],
            "usage": {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens
            }
        }

        r.setex(cache_key, 3600, json.dumps(resp_payload))
        return JSONResponse(content=resp_payload)
    
    except Exception as e:
        # Print error for local debugging
        print(f"❌ LLM Error: {e}")
        import traceback
        traceback.print_exc()

        # Log error to MLflow but do NOT fail the span (let it record the error)
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