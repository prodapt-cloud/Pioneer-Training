# Notebook Update Guide

## Overview
This guide explains how to update the `Lab1_Production_LLMOps_Endpoint_OpenAI.ipynb` notebook to load OpenAI API keys from the `secrets` folder instead of environment variables.

## Quick Start

### 1. Set up your secrets folder
```bash
# Copy the example environment file
cp secrets/.env.example secrets/.env

# Edit secrets/.env and add your OpenAI API key
# OPENAI_API_KEY=sk-proj-...your-actual-key...
```

### 2. Update the notebook cells

Open `Lab1_Production_LLMOps_Endpoint_OpenAI.ipynb` and make the following changes:

#### Change 1: Update Setup Instructions (First markdown cell)

**Find this section:**
```markdown
Setup Requirements:
```bash
# Set your OpenAI API key as an environment variable
export OPENAI_API_KEY='your-api-key-here'
# Or on Windows PowerShell:
$env:OPENAI_API_KEY='your-api-key-here'
```
```

**Replace with:**
```markdown
Setup Requirements:
```bash
# Set up your OpenAI API key in the secrets folder
# 1. Copy the example file:
cp secrets/.env.example secrets/.env

# 2. Edit secrets/.env and add your actual OpenAI API key:
# OPENAI_API_KEY=sk-proj-...your-actual-key...

# 3. The notebook will automatically load it from secrets/.env
```
```

#### Change 2: Update Section Header

**Find:**
```markdown
## 1. Configure OpenAI API Key
```

**Replace with:**
```markdown
## 1. Configure OpenAI API Key from Secrets Folder

We'll load the OpenAI API key from the `secrets/.env` file for better security and configuration management.
```

#### Change 3: Update the Code Cell

**Find this code cell:**
```python
# Check if OpenAI API key is set
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
if not OPENAI_API_KEY:
    raise ValueError(
        "OPENAI_API_KEY environment variable not set!\n"
        "Set it with: export OPENAI_API_KEY='your-key-here' (Linux/Mac)\n"
        "Or: $env:OPENAI_API_KEY='your-key-here' (Windows PowerShell)"
    )

# Initialize OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)
print("✓ OpenAI client initialized successfully!")
```

**Replace with:**
```python
# Load environment variables from secrets folder
from load_env import load_env_from_secrets, get_openai_api_key

try:
    # Load all environment variables from secrets/.env
    env_vars = load_env_from_secrets()
    print("✓ Environment variables loaded from secrets/.env")
    print(f"✓ Found {len(env_vars)} variables")
    
    # Get the OpenAI API key
    OPENAI_API_KEY = get_openai_api_key()
    print(f"✓ OPENAI_API_KEY loaded: {'*' * 20}{OPENAI_API_KEY[-4:]}")
    
except FileNotFoundError as e:
    print("❌ Error: secrets/.env file not found!")
    print("\nPlease follow these steps:")
    print("1. Copy secrets/.env.example to secrets/.env")
    print("2. Edit secrets/.env and add your OpenAI API key")
    print("3. Get your API key from: https://platform.openai.com/api-keys")
    raise

except ValueError as e:
    print(f"❌ Error: {e}")
    print("\nPlease add your OPENAI_API_KEY to secrets/.env")
    raise

# Initialize OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)
print("✓ OpenAI client initialized successfully!")
```

### 3. Save and test

1. Save the notebook
2. Run the updated cells to verify the secrets are loaded correctly
3. You should see output like:
   ```
   ✓ Environment variables loaded from secrets/.env
   ✓ Found 1 variables
   ✓ OPENAI_API_KEY loaded: ********************xyz1
   ✓ OpenAI client initialized successfully!
   ```

## Benefits of This Approach

✅ **Better Security**: API keys are stored in a dedicated secrets folder, not in environment variables  
✅ **Version Control Safe**: `.gitignore` prevents committing actual secrets  
✅ **Easy Setup**: Simple copy-paste workflow with `.env.example`  
✅ **Clear Documentation**: README in secrets folder explains setup  
✅ **Validation**: Automatic checking for required variables  

## Troubleshooting

### Error: "secrets/.env file not found"
- Make sure you copied `secrets/.env.example` to `secrets/.env`
- Check that you're running the notebook from the project root directory

### Error: "Missing required environment variables"
- Open `secrets/.env` and make sure `OPENAI_API_KEY` is set
- Ensure there are no typos in the variable name
- Make sure the value is not empty

### Error: "OPENAI_API_KEY not found in environment"
- Make sure you ran the cell that calls `load_env_from_secrets()` first
- Check that the `load_env.py` file exists in the project root

## Alternative: Run the Helper Script

You can also run the helper script to see the exact changes needed:

```bash
python update_notebook_instructions.py
```

This will print out all the changes you need to make to the notebook.
