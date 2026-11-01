# Loads MOTHERDUCK_TOKEN from the repo-root .env into this shell session, then runs dbt
# from the uv environment. Works from any folder.
# Usage:
#   .\dbt\run_dbt.ps1 debug
#   .\dbt\run_dbt.ps1 build --select fo_calendar
#   .\dbt\run_dbt.ps1 build --target prod   # only when you mean it

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

uv run --project (Join-Path $PSScriptRoot "..") --group dbt dbt @args --project-dir $PSScriptRoot --profiles-dir $PSScriptRoot
