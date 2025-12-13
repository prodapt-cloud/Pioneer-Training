import json
import os

nb_path = r'd:\Workspace\pioneer\Pioneer-Training\llmops\Lab3-LLMSecOps-Attack-Defense\notebook.ipynb'

with open(nb_path, 'r', encoding='utf-8') as f:
    nb = json.load(f)

cells = nb['cells']

# 1. Update pip install cell
for cell in cells:
    if cell['cell_type'] == 'code' and "pip install" in "".join(cell['source']):
        source = "".join(cell['source'])
        if "uvicorn" not in source:
            cell['source'] = [
                "!pip install --quiet requests beautifulsoup4 pypdf presidio-analyzer presidio-anonymizer nemo-guardrails bleach openai langchain-openai python-dotenv uvicorn python-multipart fastapi"
            ]
        break

# 2. Remove Duplicate Env Var Cell
# We look for cells that have "load_dotenv()" and "Verify keys are presence"
env_indices = []
for i, cell in enumerate(cells):
    if cell['cell_type'] == 'code' and "Verify keys are presence" in "".join(cell['source']):
        env_indices.append(i)

if len(env_indices) > 1:
    # Remove all but the first one, in reverse order to maintain indices
    print(f"Found {len(env_indices)} env var cells. Removing duplicates.")
    for i in sorted(env_indices[1:], reverse=True):
        del cells[i]

with open(nb_path, 'w', encoding='utf-8') as f:
    json.dump(nb, f, indent=4)
print("Notebook repaired.")
