# Secrets Folder

This folder contains environment configuration files for the LLMOps pipeline.

**Supports both OpenAI and Azure OpenAI!**

## Setup Instructions

### 1. Copy the example file
```bash
cp .env.example .env
```

### 2. Choose your LLM provider

Edit `.env` and set `LLM_PROVIDER` to either `openai` or `azure`:

```bash
LLM_PROVIDER=openai   # For standard OpenAI
# OR
LLM_PROVIDER=azure    # For Azure OpenAI
```

### 3. Configure your chosen provider

#### Option A: Using OpenAI

1. Get your API key from https://platform.openai.com/api-keys
2. Add it to `.env`:
   ```bash
   OPENAI_API_KEY=sk-proj-...your-actual-key...
   ```

#### Option B: Using Azure OpenAI

1. Go to Azure Portal → Your Azure OpenAI Resource → Keys and Endpoint
2. Add the following to `.env`:
   ```bash
   AZURE_OPENAI_API_KEY=your-azure-key
   AZURE_OPENAI_ENDPOINT=https://your-resource-name.openai.azure.com/
   AZURE_OPENAI_API_VERSION=2024-02-15-preview
   AZURE_OPENAI_DEPLOYMENT_NAME=gpt-35-turbo
   ```

## Security Notes

- ⚠️ **Never commit `.env` to git** - it contains your secret API keys
- ✅ The `.gitignore` file ensures `.env` is excluded from version control
- ✅ Only `.env.example` (without real keys) should be committed
- 🔒 Keep your API keys secure and rotate them if exposed

## Environment Variables

### Provider Selection

| Variable | Required | Description |
|----------|----------|-------------|
| `LLM_PROVIDER` | Yes | Choose `openai` or `azure` |

### OpenAI Configuration (when `LLM_PROVIDER=openai`)

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | Yes | Your OpenAI API key for accessing GPT models |
| `OPENAI_ORG_ID` | No | Organization ID (if part of multiple orgs) |
| `OPENAI_MODEL` | No | Default model to use (e.g., gpt-3.5-turbo, gpt-4) |

### Azure OpenAI Configuration (when `LLM_PROVIDER=azure`)

| Variable | Required | Description |
|----------|----------|-------------|
| `AZURE_OPENAI_API_KEY` | Yes | Your Azure OpenAI API key |
| `AZURE_OPENAI_ENDPOINT` | Yes | Azure OpenAI endpoint URL |
| `AZURE_OPENAI_API_VERSION` | Yes | API version (e.g., 2024-02-15-preview) |
| `AZURE_OPENAI_DEPLOYMENT_NAME` | Yes | Name of your model deployment in Azure |
| `AZURE_OPENAI_GPT4_DEPLOYMENT` | No | Deployment name for GPT-4 (if different) |
| `AZURE_OPENAI_EMBEDDING_DEPLOYMENT` | No | Deployment name for embeddings |

## Testing Your Configuration

Run the environment loader to test your setup:

```bash
python load_env.py
```

**Expected output for OpenAI:**
```
✓ Environment variables loaded successfully!
✓ Found 2 variables
✓ LLM Provider: OPENAI
✓ OPENAI_API_KEY: ********************xyz1
✓ OpenAI client initialized (key: ...xyz1)
✓ Client initialized successfully!
```

**Expected output for Azure OpenAI:**
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

