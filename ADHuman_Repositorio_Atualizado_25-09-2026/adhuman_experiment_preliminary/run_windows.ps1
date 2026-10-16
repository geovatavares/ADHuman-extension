$ErrorActionPreference = "Stop"

if (!(Test-Path ".\.venv\Scripts\python.exe")) {
    Write-Host "Ambiente .venv nao encontrado. Execute primeiro .\setup_windows.ps1"
    exit 1
}

Write-Host "[1/3] Descobrindo/fixando 10 paginas por site..."
& ".\.venv\Scripts\python.exe" run_experiment.py --discover-only
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[2/3] Executando experimento..."
& ".\.venv\Scripts\python.exe" run_experiment.py --mode extension
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[3/3] Gerando analise..."
& ".\.venv\Scripts\python.exe" analyze_results.py
