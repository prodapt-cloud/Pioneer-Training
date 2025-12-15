import json
import urllib.request as u

pkgs = [
    'openai','azure-ai-openai','azure-ai-contentsafety','azure-core','pydantic',
    'langchain','langchain-community','nemoguardrails','transformers','torch','accelerate',
    'chromadb','sentence-transformers','faiss-cpu','scikit-learn','gensim','hnswlib','nmslib','python-annoy','annoy'
]

print('Checking packages for "annoy" in requires_dist...')
for p in pkgs:
    try:
        data = json.load(u.urlopen(f'https://pypi.org/pypi/{p}/json'))
        reqs = data['info'].get('requires_dist') or []
        hits = [r for r in reqs if 'annoy' in (r or '').lower()]
        if hits:
            print(f"{p}: {hits}")
    except Exception as e:
        print(f"error {p}: {e}")

print('Done')
