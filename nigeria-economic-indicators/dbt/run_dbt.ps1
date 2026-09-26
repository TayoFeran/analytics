# Loads MOTHERDUCK_TOKEN from ../.env into this shell session, then runs dbt.
# Usage (from inside the dbt/ folder):
#   .\run_dbt.ps1 debug
#   .\run_dbt.ps1 run
#   .\run_dbt.ps1 test

$envFile = Join-Path $PSScriptRoot "..\.env"

if (Test-Path $envFile) {
    Get-Content $envFile | ForEach-Object {
        if ($_ -match '^\s*([^#=][^=]*)=(.*)$') {
            $key = $matches[1].Trim()
            $value = $matches[2].Trim()
            [System.Environment]::SetEnvironmentVariable($key, $value, "Process")
        }
    }
} else {
    Write-Warning "No .env file found at $envFile"
}

dbt @args --profiles-dir $PSScriptRoot