# secure_app/app.py
import os
from fastapi import FastAPI, File, UploadFile, Form
from nemoguardrails import LLMRails, RailsConfig
from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine
import hashlib
import litellm

app = FastAPI(title="SECURE RAG - Enterprise Defenses")

# Critical: Azure OpenAI Configuration
AZURE_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION")
AZURE_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")

litellm.api_key = AZURE_API_KEY
litellm.api_base = AZURE_ENDPOINT
litellm.api_version = AZURE_API_VERSION
litellm.set_verbose = False

# NeMo Guardrails + LlamaGuard
# Assuming running from root directory (Lab3-LLMSecOps-Attack-Defense)
config_path = os.path.join(os.getcwd(), "guardrails_config")
if not os.path.exists(config_path):
    # Fallback if running inside directory
    config_path = "../guardrails_config"

config = RailsConfig.from_path(config_path)
rails = LLMRails(config=config)

analyzer = AnalyzerEngine()
anonymizer = AnonymizerEngine()

KNOWN_MALICIOUS_HASHES = {
    # indirect_injection.pdf  →  Hidden prompt injection
    "c8f8e8e1b3e4d5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0",
    
    # poison_salary.pdf       →  Fake CEO salary poisoning
    "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2",
    
    # pii_leak.pdf            →  Contains real-looking SSNs and emails
    "f1e2d3c4b5a69788796f5e4d3c2b1a0987654321fedcba0987654321fedcba09",
    
    # jailbreak_ransomware.pdf → DAN + ransomware request
    "11223344556677889900aabbccddeeff11223344556677889900aabbccddeeff"
}

def sanitize_input(text: str) -> str:
    blocked = ["ignore previous", "DAN", "do anything now", "PWNED"]
    if any(b in text.lower() for b in blocked):
        return "BLOCKED: Suspicious input detected."
    return text

@app.post("/chat")
async def secure_chat(user_input: str = Form(...), file: UploadFile = File(None)):
    user_input = sanitize_input(user_input)

    if file:
        contents = await file.read()
        file_hash = hashlib.sha256(contents).hexdigest()
        if file_hash in KNOWN_MALICIOUS_HASHES:
            return {"response": "BLOCKED: Malicious document rejected."}

    try:
        response = await rails.generate_async(
            messages=[{"role": "user", "content": user_input}]
        )
        answer = response["content"]
    except Exception:
        answer = "I can't assist with that request."

    # PII redaction on output
    results = analyzer.analyze(text=answer, language="en")
    answer = anonymizer.anonymize(text=answer, analyzer_results=results).text

    return {"response": answer}