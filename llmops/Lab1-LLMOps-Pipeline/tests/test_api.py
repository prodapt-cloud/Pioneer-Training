import requests
import time

def test_chat_endpoint():
    payload = {
        "messages": [{"role": "user", "content": "Hello"}],
        "metadata": {"department": "engineering"}
    }
    start = time.time()
    r1 = requests.post("http://localhost:8080/v1/chat/completions", json=payload)
    t1 = time.time() - start

    start = time.time()
    r2 = requests.post("http://localhost:8080/v1/chat/completions", json=payload)
    t2 = time.time() - start

    assert r1.status_code == 200
    assert r2.status_code == 200
    assert t2 < t1 * 0.5  # Cache should be 2x+ faster
    print("All tests passed! Cache working!")