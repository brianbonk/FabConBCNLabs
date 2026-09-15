# Thin launcher for provision_fabric_iq.py on Windows PowerShell.
#
# Usage:
#   .\run-setup.ps1
#   .\run-setup.ps1 -- --dry-run
#   .\run-setup.ps1 -- --non-interactive --capacity "My Capacity" --workspace-name "Fabric IQ"
#
# All arguments are passed straight through to provision_fabric_iq.py --
# see setup/README.md for the full flag reference.

$ErrorActionPreference = "Stop"

$python = Get-Command python3 -ErrorAction SilentlyContinue
if (-not $python) {
    $python = Get-Command python -ErrorAction SilentlyContinue
}
if (-not $python) {
    Write-Error "python3 (or python) was not found on your PATH. Install Python 3.10+ (see ..\prerequisites\PREREQUISITES.md, section 3) and re-run."
    exit 1
}

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$provisionScript = Join-Path $scriptDir "provision_fabric_iq.py"

& $python.Path $provisionScript @args
exit $LASTEXITCODE
