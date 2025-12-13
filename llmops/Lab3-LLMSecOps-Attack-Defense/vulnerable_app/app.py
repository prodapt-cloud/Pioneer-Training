# vulnerable_app/app.py
import os
from fastapi import FastAPI, File, UploadFile, Form
from langchain_community.vectorstores import Chroma
# from langchain_community.embeddings import OllamaEmbeddings
from langchain_community.embeddings import AzureOpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader
import litellm

app = FastAPI(title="Vulnerable RAG - NO DEFENSES")

# Azure Configuration
# Ensure these are set before importing or running
AZURE_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION")
AZURE_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")
AZURE_EMBEDDING_DEPLOYMENT = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME")

if not AZURE_API_KEY:
    print("WARNING: AZURE_OPENAI_API_KEY not found. App may fail.")

litellm.api_key = AZURE_API_KEY
litellm.api_base = AZURE_ENDPOINT
litellm.api_version = AZURE_API_VERSION
litellm.set_verbose = False

embeddings = AzureOpenAIEmbeddings(
    azure_deployment=AZURE_EMBEDDING_DEPLOYMENT,
    openai_api_version=AZURE_API_VERSION,
    azure_endpoint=AZURE_ENDPOINT,
    api_key=AZURE_API_KEY,
)
# Use local directory relative to execution or temp
db = Chroma(persist_directory="./data/chroma_vulnerable", embedding_function=embeddings)

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
        model=f"azure/{AZURE_DEPLOYMENT}",
        messages=[{"role": "user", "content": prompt}]
    )

    return {"response": response.choices[0].message.content}