$ErrorActionPreference = "Stop"

if (Get-Command python -ErrorAction SilentlyContinue) {
    python .\retry_reassignment.py
} elseif (Get-Command py -ErrorAction SilentlyContinue) {
    py .\retry_reassignment.py
} else {
    Write-Error "Python was not found in PATH. Install Python or add it to PATH, then run this script again."
}
