# Run this to start MLflow UI
import subprocess
import os
os.makedirs("mlflow", exist_ok=True)
subprocess.run(["mlflow", "ui", "--backend-store-uri", "file:./mlflow", "--port", "5000"])