# Azure OpenAI Support Guide

## Overview

The LLMOps pipeline now supports **both OpenAI and Azure OpenAI**! You can easily switch between providers by changing a single configuration variable.

## Quick Start

### 1. Set up your secrets folder

```bash
# Copy the example file
cp secrets/.env.example secrets/.env
```

### 2. Choose your provider

Edit `secrets/.env` and set `LLM_PROVIDER`:

```bash
# For standard OpenAI
LLM_PROVIDER=openai

# OR for Azure OpenAI
LLM_PROVIDER=azure
```

### 3. Configure credentials

#### For OpenAI:
```bash
OPENAI_API_KEY=sk-proj-...your-key...
```

#### For Azure OpenAI:
```bash
AZURE_OPENAI_API_KEY=your-azure-key
AZURE_OPENAI_ENDPOINT=https://your-resource-name.openai.azure.com/
AZURE_OPENAI_API_VERSION=2024-02-15-preview
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-35-turbo
```

## Getting Azure OpenAI Credentials

1. **Go to Azure Portal**: https://portal.azure.com
2. **Navigate to your Azure OpenAI resource**
3. **Get your credentials:**
   - **API Key**: Resource → Keys and Endpoint → KEY 1 or KEY 2
   - **Endpoint**: Resource → Keys and Endpoint → Endpoint
   - **Deployment Name**: Resource → Model deployments → Your deployment name

## Notebook Updates

### Change 1: Update Setup Instructions

**Find:**
```markdown
Setup Requirements:
```bash
# Set your OpenAI API key as an environment variable
...
```
```

**Replace with:**
```markdown
Setup Requirements:
```bash
# Set up your LLM provider in the secrets folder
# 1. Copy the example file:
cp secrets/.env.example secrets/.env

# 2. Edit secrets/.env and choose your provider:
#    - For OpenAI: Set LLM_PROVIDER=openai and add OPENAI_API_KEY
#    - For Azure: Set LLM_PROVIDER=azure and add Azure credentials

# 3. See secrets/README.md for detailed configuration instructions
```
```

### Change 2: Update Section Header

**Find:**
```markdown
## 1. Configure OpenAI API Key
```

**Replace with:**
```markdown
## 1. Configure LLM Provider (OpenAI or Azure OpenAI)

We'll load credentials from `secrets/.env` which supports both OpenAI and Azure OpenAI.
```

### Change 3: Update Environment Loading Code

**Replace the API key loading cell with:**

```python
# Load environment variables from secrets folder
from load_env import load_env_from_secrets, get_llm_provider, get_openai_client

try:
    # Load all environment variables from secrets/.env
    env_vars = load_env_from_secrets()
    provider = get_llm_provider()
    
    print("✓ Environment variables loaded from secrets/.env")
    print(f"✓ Found {len(env_vars)} variables")
    print(f"✓ LLM Provider: {provider.upper()}")
    
    # Initialize the appropriate client based on provider
    client = get_openai_client()
    
    # Get deployment name for Azure (needed for API calls)
    if provider == 'azure':
        import os
        DEPLOYMENT_NAME = os.getenv('AZURE_OPENAI_DEPLOYMENT_NAME')
        print(f"✓ Using deployment: {DEPLOYMENT_NAME}")
    
except FileNotFoundError as e:
    print("❌ Error: secrets/.env file not found!")
    print("\nPlease follow these steps:")
    print("1. Copy secrets/.env.example to secrets/.env")
    print("2. Edit secrets/.env and configure your LLM provider")
    print("   - For OpenAI: Set LLM_PROVIDER=openai and add OPENAI_API_KEY")
    print("   - For Azure: Set LLM_PROVIDER=azure and add Azure credentials")
    print("3. See secrets/README.md for detailed instructions")
    raise

except ValueError as e:
    print(f"❌ Error: {e}")
    print("\nPlease check your secrets/.env configuration")
    raise

print("✓ LLM client initialized successfully!")
```

### Change 4: Update generate_response Function

**Replace the generate_response function with:**

```python
def generate_response(prompt: str, model: str = None, temperature: float = 0.3, max_tokens: int = 512):
    """
    Generate a response using OpenAI or Azure OpenAI API
    
    Args:
        prompt: The user prompt
        model: Model to use (for OpenAI) or None to use Azure deployment
        temperature: Sampling temperature (0-2)
        max_tokens: Maximum tokens in response
    """
    try:
        # For Azure OpenAI, use the deployment name instead of model
        if provider == 'azure':
            response = client.chat.completions.create(
                model=DEPLOYMENT_NAME,  # Azure uses deployment name
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=max_tokens
            )
        else:
            # For OpenAI, use the model parameter
            response = client.chat.completions.create(
                model=model or "gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=max_tokens
            )
        return response.choices[0].message.content
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM API error: {str(e)}")
```

### Change 5: Update API Endpoint Handler

**In the `/v1/chat/completions` endpoint, update the generate_response call:**

```python
# Generate using the configured provider
if provider == 'azure':
    # Azure uses deployment name, not model parameter
    answer = generate_response(
        rendered_prompt,
        model=None,  # Will use DEPLOYMENT_NAME
        temperature=request.temperature,
        max_tokens=request.max_tokens
    )
else:
    # OpenAI uses model parameter
    answer = generate_response(
        rendered_prompt,
        model=request.model,
        temperature=request.temperature,
        max_tokens=request.max_tokens
    )
```

## Testing Your Setup

### Test the environment loader:

```bash
python load_env.py
```

### Expected Output for OpenAI:
```
✓ Environment variables loaded successfully!
✓ Found 2 variables
✓ LLM Provider: OPENAI
✓ OPENAI_API_KEY: ********************xyz1
✓ OpenAI client initialized (key: ...xyz1)
✓ Client initialized successfully!
```

### Expected Output for Azure OpenAI:
```
✓ Environment variables loaded successfully!
✓ Found 5 variables
✓ LLM Provider: AZURE
✓ AZURE_OPENAI_ENDPOINT: https://your-resource.openai.azure.com/
✓ AZURE_OPENAI_DEPLOYMENT: gpt-35-turbo
✓ AZURE_OPENAI_API_KEY: ********************abc1
✓ Azure OpenAI client initialized
  Endpoint: https://your-resource.openai.azure.com/
  Deployment: gpt-35-turbo
✓ Client initialized successfully!
```

## Key Differences: OpenAI vs Azure OpenAI

| Feature | OpenAI | Azure OpenAI |
|---------|--------|--------------|
| **API Key Source** | platform.openai.com | Azure Portal |
| **Endpoint** | Built-in | Custom (your-resource.openai.azure.com) |
| **Model Selection** | Pass model name (e.g., "gpt-4") | Use deployment name |
| **API Version** | Automatic | Must specify (e.g., 2024-02-15-preview) |
| **Billing** | OpenAI account | Azure subscription |
| **Data Location** | OpenAI servers | Your Azure region |
| **Enterprise Features** | Limited | Full Azure integration |

## Switching Between Providers

To switch providers, simply change `LLM_PROVIDER` in `secrets/.env`:

```bash
# Switch to OpenAI
LLM_PROVIDER=openai

# Switch to Azure
LLM_PROVIDER=azure
```

No code changes needed - the `load_env.py` utility handles everything!

## Troubleshooting

### Error: "Missing required Azure OpenAI variables"
- Make sure all 4 Azure variables are set in `secrets/.env`
- Check for typos in variable names
- Ensure values are not empty

### Error: "Invalid LLM_PROVIDER"
- `LLM_PROVIDER` must be exactly `openai` or `azure` (lowercase)
- Check for extra spaces or quotes

### Azure API Error: "Deployment not found"
- Verify `AZURE_OPENAI_DEPLOYMENT_NAME` matches your Azure deployment
- Check Azure Portal → Your Resource → Model deployments

### Azure API Error: "Invalid endpoint"
- Ensure `AZURE_OPENAI_ENDPOINT` ends with `/`
- Format: `https://your-resource-name.openai.azure.com/`

## Additional Resources

- [OpenAI API Documentation](https://platform.openai.com/docs)
- [Azure OpenAI Documentation](https://learn.microsoft.com/en-us/azure/ai-services/openai/)
- [Azure OpenAI Quickstart](https://learn.microsoft.com/en-us/azure/ai-services/openai/quickstart)
