
import os
import sys

# Mock environment before importing main
os.environ["MLFLOW_ENABLED"] = "true"
os.environ["MLFLOW_TRACKING_URI"] = "http://this-does-not-exist-12345.com:5000"
os.environ["REDIS_ENABLED"] = "false"
os.environ["OTEL_ENABLED"] = "false"

print("🧪 Testing app startup with unreachable MLflow...")

try:
    # Adding project root to path
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
    
    from app.main import app, MLFLOW_ENABLED
    
    print("✅ App module imported successfully!")
    print(f"   MLFLOW_ENABLED status: {MLFLOW_ENABLED}")
    
    if MLFLOW_ENABLED is False:
        print("✅ MLflow correctly disabled itself upon failure.")
    else:
        # Note: mlflow.set_tracking_uri might not throw immediately for HTTP, 
        # but set_experiment usually does (or warns). 
        # If it didn't throw, we assume safe startup.
        print("⚠️  MLflow did not fail initialization (lazy connect?), but app didn't crash.")
        
except Exception as e:
    print(f"❌ App crashed during startup: {e}")
    sys.exit(1)
