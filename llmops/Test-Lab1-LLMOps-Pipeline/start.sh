docker run -d --name redis -p 6379:6379 redis:7
ollama serve & ollama pull llama3.2:3b
uvicorn app.main:app --reload