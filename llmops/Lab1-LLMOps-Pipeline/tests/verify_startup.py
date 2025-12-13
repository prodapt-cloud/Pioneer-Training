import os
import sys
import uvicorn
import time
import requests
import threading
from dotenv import load_dotenv

# Add app directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../app'))

def run_server():
    print("🚀 Starting Uvicorn server...")
    try:
        # Load environment variables from secrets/.env if it exists
        env_path = os.path.join(os.path.dirname(__file__), '../secrets/.env')
        if os.path.exists(env_path):
            print(f"📄 Loading environment from {env_path}")
            load_dotenv(env_path)
        else:
            print("⚠️  No .env file found in secrets/.env, using existing env vars or defaults")

        # Set necessary dummy env vars if not set, to prevent immediate crash if logic depends on them
        # (Though main.py seems to handle missing vars gracefully in most cases)
        if "REDIS_HOST" not in os.environ:
            os.environ["REDIS_HOST"] = "localhost" # Fallback
        
        # Import directly to test import errors first
        print("📦 Attempting to import app.main...")
        import main
        print(f"📄 Loaded main from: {main.__file__}")
        from main import app
        print("✅ Import successful!")
        
        # Run server
        uvicorn.run(app, host="0.0.0.0", port=8000)
    except Exception as e:
        print(f"❌ Application failed to start: {e}")
        import traceback
        traceback.print_exc()
        os._exit(1)

if __name__ == "__main__":
    t = threading.Thread(target=run_server, daemon=True)
    t.start()
    
    # Wait a bit for startup
    print("⏳ Waiting for server to start...")
    time.sleep(5)
    
    try:
        print("💓 Checking health endpoint...")
        response = requests.get("http://localhost:8000/health")
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        
        if response.status_code == 200:
            print("✅ Server is healthy!")
        else:
            print("❌ Server unhealthy")
            
    except requests.exceptions.ConnectionError:
        print("❌ Connection refused. Server probably crashed or didn't start.")
    except Exception as e:
        print(f"❌ Error Checking health: {e}")
    
    # Keep alive for a moment if needed or just exit
    # os._exit(0)
