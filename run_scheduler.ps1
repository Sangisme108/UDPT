$ErrorActionPreference = "Stop"

if (Get-Command python -ErrorAction SilentlyContinue) {
    python .\load_scheduler.py
} elseif (Get-Command py -ErrorAction SilentlyContinue) {
    py .\load_scheduler.py
} else {
    Write-Error "Python was not found in PATH. Install Python or add it to PATH, then run this script again."
}
