
import os
import sys
from dotenv import load_dotenv

# Add app to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

# Load secrets
dotenv_path = os.path.join(os.path.dirname(__file__), '..', 'secrets', '.env')
if os.path.exists(dotenv_path):
    print(f"Loading secrets from {dotenv_path}")
    load_dotenv(dotenv_path)
else:
    print(f"Warning: {dotenv_path} not found")

from app.eval_ragas import run_evaluation

if __name__ == "__main__":
    run_evaluation()
