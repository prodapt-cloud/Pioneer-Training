"""
Environment loader for LLMOps Pipeline
Loads environment variables from secrets/.env file
Supports both OpenAI and Azure OpenAI
"""
import os
from pathlib import Path
from typing import Optional, Dict, Literal


def load_env_from_secrets(secrets_dir: str = "secrets", env_file: str = ".env") -> dict:
    """
    Load environment variables from secrets folder
    
    Args:
        secrets_dir: Directory containing the .env file (default: "secrets")
        env_file: Name of the environment file (default: ".env")
    
    Returns:
        dict: Dictionary of environment variables loaded
    
    Raises:
        FileNotFoundError: If .env file doesn't exist
        ValueError: If required variables are missing
    """
    # Get the project root directory (where this script is located)
    project_root = Path(__file__).parent
    env_path = project_root / secrets_dir / env_file
    
    if not env_path.exists():
        raise FileNotFoundError(
            f"Environment file not found: {env_path}\n"
            f"Please create it by copying secrets/.env.example to secrets/.env\n"
            f"and adding your API keys."
        )
    
    # Load environment variables
    env_vars = {}
    with open(env_path, 'r') as f:
        for line in f:
            line = line.strip()
            # Skip comments and empty lines
            if not line or line.startswith('#'):
                continue
            
            # Parse KEY=VALUE
            if '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip()
                
                # Remove quotes if present
                if value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]
                elif value.startswith("'") and value.endswith("'"):
                    value = value[1:-1]
                
                # Set environment variable
                os.environ[key] = value
                env_vars[key] = value
    
    # Validate based on provider
    provider = env_vars.get('LLM_PROVIDER', 'openai').lower()
    
    if provider == 'openai':
        required_vars = ['OPENAI_API_KEY']
        missing_vars = [var for var in required_vars if var not in env_vars or not env_vars[var]]
        
        if missing_vars:
            raise ValueError(
                f"Missing required OpenAI variables: {', '.join(missing_vars)}\n"
                f"Please add them to {env_path}"
            )
    elif provider == 'azure':
        required_vars = ['AZURE_OPENAI_API_KEY', 'AZURE_OPENAI_ENDPOINT', 
                        'AZURE_OPENAI_API_VERSION', 'AZURE_OPENAI_DEPLOYMENT_NAME']
        missing_vars = [var for var in required_vars if var not in env_vars or not env_vars[var]]
        
        if missing_vars:
            raise ValueError(
                f"Missing required Azure OpenAI variables: {', '.join(missing_vars)}\n"
                f"Please add them to {env_path}"
            )
    else:
        raise ValueError(
            f"Invalid LLM_PROVIDER: {provider}\n"
            f"Must be either 'openai' or 'azure'"
        )
    
    return env_vars


def get_llm_provider() -> Literal['openai', 'azure']:
    """
    Get the configured LLM provider
    
    Returns:
        str: Either 'openai' or 'azure'
    """
    provider = os.getenv('LLM_PROVIDER', 'openai').lower()
    if provider not in ['openai', 'azure']:
        raise ValueError(f"Invalid LLM_PROVIDER: {provider}. Must be 'openai' or 'azure'")
    return provider


def get_openai_api_key() -> str:
    """
    Get OpenAI API key from environment
    
    Returns:
        str: OpenAI API key
    
    Raises:
        ValueError: If API key is not set or provider is not OpenAI
    """
    provider = get_llm_provider()
    if provider != 'openai':
        raise ValueError(
            f"LLM_PROVIDER is set to '{provider}', but you're trying to get OpenAI credentials.\n"
            f"Either change LLM_PROVIDER to 'openai' or use get_azure_openai_config()"
        )
    
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        raise ValueError(
            "OPENAI_API_KEY not found in environment.\n"
            "Run load_env_from_secrets() first to load from secrets/.env"
        )
    return api_key


def get_azure_openai_config() -> Dict[str, str]:
    """
    Get Azure OpenAI configuration from environment
    
    Returns:
        dict: Dictionary with Azure OpenAI configuration
            - api_key: Azure OpenAI API key
            - endpoint: Azure OpenAI endpoint URL
            - api_version: Azure OpenAI API version
            - deployment_name: Azure OpenAI deployment name
    
    Raises:
        ValueError: If required config is not set or provider is not Azure
    """
    provider = get_llm_provider()
    if provider != 'azure':
        raise ValueError(
            f"LLM_PROVIDER is set to '{provider}', but you're trying to get Azure credentials.\n"
            f"Either change LLM_PROVIDER to 'azure' or use get_openai_api_key()"
        )
    
    config = {
        'api_key': os.getenv('AZURE_OPENAI_API_KEY'),
        'endpoint': os.getenv('AZURE_OPENAI_ENDPOINT'),
        'api_version': os.getenv('AZURE_OPENAI_API_VERSION'),
        'deployment_name': os.getenv('AZURE_OPENAI_DEPLOYMENT_NAME'),
    }
    
    missing = [k for k, v in config.items() if not v]
    if missing:
        raise ValueError(
            f"Missing required Azure OpenAI config: {', '.join(missing)}\n"
            f"Run load_env_from_secrets() first to load from secrets/.env"
        )
    
    return config


def get_openai_client():
    """
    Get the appropriate OpenAI client based on the provider
    
    Returns:
        OpenAI or AzureOpenAI client instance
    
    Raises:
        ImportError: If openai package is not installed
        ValueError: If configuration is invalid
    """
    try:
        from openai import OpenAI, AzureOpenAI
    except ImportError:
        raise ImportError(
            "OpenAI package not installed.\n"
            "Install it with: pip install openai"
        )
    
    provider = get_llm_provider()
    
    if provider == 'openai':
        api_key = get_openai_api_key()
        org_id = os.getenv('OPENAI_ORG_ID')
        client = OpenAI(api_key=api_key, organization=org_id)
        print(f"✓ OpenAI client initialized (key: ...{api_key[-4:]})")
        return client
    
    elif provider == 'azure':
        config = get_azure_openai_config()
        client = AzureOpenAI(
            api_key=config['api_key'],
            api_version=config['api_version'],
            azure_endpoint=config['endpoint']
        )
        print(f"✓ Azure OpenAI client initialized")
        print(f"  Endpoint: {config['endpoint']}")
        print(f"  Deployment: {config['deployment_name']}")
        return client


if __name__ == "__main__":
    # Test the loader
    try:
        env_vars = load_env_from_secrets()
        provider = get_llm_provider()
        
        print("✓ Environment variables loaded successfully!")
        print(f"✓ Found {len(env_vars)} variables")
        print(f"✓ LLM Provider: {provider.upper()}")
        
        if provider == 'openai':
            api_key = get_openai_api_key()
            print(f"✓ OPENAI_API_KEY: {'*' * 20}{api_key[-4:]}")
        elif provider == 'azure':
            config = get_azure_openai_config()
            print(f"✓ AZURE_OPENAI_ENDPOINT: {config['endpoint']}")
            print(f"✓ AZURE_OPENAI_DEPLOYMENT: {config['deployment_name']}")
            print(f"✓ AZURE_OPENAI_API_KEY: {'*' * 20}{config['api_key'][-4:]}")
        
        # Try to initialize client
        print("\nTesting client initialization...")
        client = get_openai_client()
        print("✓ Client initialized successfully!")
        
    except Exception as e:
        print(f"✗ Error: {e}")

