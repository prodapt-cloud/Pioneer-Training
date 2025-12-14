
# Load secrets from .env file
$envFile = Join-Path $PSScriptRoot "secrets\.env"
if (Test-Path $envFile) {
    Write-Host "Loading secrets from $envFile"
    Get-Content $envFile | ForEach-Object {
        if ($_ -match '^([^#=]+)=(.*)') {
            $name = $matches[1].Trim()
            $value = $matches[2].Trim()
            [Environment]::SetEnvironmentVariable($name, $value)
        }
    }
} else {
    Write-Warning ".env file not found at $envFile"
}

# Run the server
Write-Host "Starting Uvicorn server..."
python -m uvicorn app.main:app --port 8000 --reload
