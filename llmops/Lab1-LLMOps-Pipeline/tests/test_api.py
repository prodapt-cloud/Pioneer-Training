import requests
import time
import pytest

import os

# Base URL for API (default to localhost:8080 for CI port-forward)
BASE_URL = os.getenv("API_URL", "http://localhost:8080")

def test_health_endpoint():
    """Test that the API is running and healthy"""
    print(f"Testing against: {BASE_URL}")
    r = requests.get(f"{BASE_URL}/health")
    assert r.status_code in [200, 503]  # 503 if Redis not connected
    data = r.json()
    assert "status" in data
    assert "llm_provider" in data
    print(f"✅ Health check passed: {data}")

def test_chat_endpoint():
    """Test chat endpoint - skip if LLM not configured"""
    # First check if LLM is configured
    health = requests.get(f"{BASE_URL}/health").json()
    
    if health.get("llm_provider") == "none":
        pytest.skip("LLM not configured (no API keys set in GitHub Secrets)")
    
    payload = {
        "messages": [{"role": "user", "content": "Hello"}],
        "metadata": {"department": "engineering"}
    }
    
    print(f"Testing with LLM provider: {health.get('llm_provider')}")
    
    start = time.time()
    start = time.time()
    r1 = requests.post(f"{BASE_URL}/v1/chat/completions", json=payload)
    t1 = time.time() - start

    # Should succeed if LLM is configured
    assert r1.status_code == 200, f"Expected 200, got {r1.status_code}: {r1.text}"
    
    start = time.time()
    r2 = requests.post(f"{BASE_URL}/v1/chat/completions", json=payload)
    t2 = time.time() - start

    assert r2.status_code == 200
    assert t2 < t1 * 0.5, f"Cache not working: t1={t1:.2f}s, t2={t2:.2f}s"
    print(f"✅ All tests passed! Cache working! (t1={t1:.2f}s, t2={t2:.2f}s)")