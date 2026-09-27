# Thin launcher for check_environment.py on Windows PowerShell.
#
# Usage:
#   .\check-environment.ps1
#   .\check-environment.ps1 --install-deps
#
# All arguments are passed straight through to check_environment.py --
# see setup/README.md for details.

$ErrorActionPreference = "Stop"

$python = Get-Command python3 -ErrorAction SilentlyContinue
if (-not $python) {
    $python = Get-Command python -ErrorAction SilentlyContinue
}
if (-not $python) {
    Write-Error "python3 (or python) was not found on your PATH. Install Python 3.10-3.13 (see ..\prerequisites\PREREQUISITES.md, section 1) and re-run."
    exit 1
}

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$checkScript = Join-Path $scriptDir "check_environment.py"

& $python.Path $checkScript @args
exit $LASTEXITCODE
