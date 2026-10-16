$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$VenvPython = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $VenvPython)) {
    throw "Backend nao instalado. Execute primeiro 1-Instalar-Backend.bat."
}

Write-Host "Iniciando o ADHuman Visual 3.1 em http://127.0.0.1:8000"
Write-Host "Mantenha esta janela aberta enquanto usar a extensao do Chrome."
Write-Host ""

& $VenvPython -m uvicorn app.main:app `
    --host 127.0.0.1 `
    --port 8000

if ($LASTEXITCODE -ne 0) {
    throw "O backend do ADHuman foi encerrado com um erro."
}
