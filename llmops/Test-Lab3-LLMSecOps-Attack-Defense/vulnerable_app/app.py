# vulnerable_app/app.py
import os
from fastapi import FastAPI, File, UploadFile, Form
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import OllamaEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader
import litellm

app = FastAPI(title="Vulnerable RAG - NO DEFENSES")

# Respect OLLAMA_HOST from docker-compose
OLLAMA_BASE_URL = os.getenv("OLLAMA_HOST", "http://localhost:11434")
litellm.api_base = OLLAMA_BASE_URL  # This is the key line!
litellm.set_verbose = False

embeddings = OllamaEmbeddings(model="llama3.2:3b", base_url=OLLAMA_BASE_URL)
db = Chroma(persist_directory="/data", embedding_function=embeddings)

@app.post("/chat")
async def chat(user_input: str = Form(...), file: UploadFile = File(None)):
    if file:
        contents = await file.read()
        path = f"/tmp/{file.filename}"
        with open(path, "wb") as f:
            f.write(contents)
        loader = PyPDFLoader(path)
        docs = loader.load_and_split(RecursiveCharacterTextSplitter(chunk_size=500))
        db.add_documents(docs)

    results = db.similarity_search(user_input, k=4)
    context = "\n\n".join([d.page_content for d in results])

    prompt = f"Context: {context}\n\nQuestion: {user_input}\nAnswer:"

    response = litellm.completion(
        model="ollama/llama3.2:3b",        # model name stays the same
        messages=[{"role": "user", "content": prompt}]
    )

    return {"response": response.choices[0].message.content}