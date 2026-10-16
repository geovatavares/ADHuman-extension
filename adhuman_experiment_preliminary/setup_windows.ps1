$ErrorActionPreference = "Stop"

Write-Host "[1/4] Procurando Python 3.11..."
$py = "py"
try {
    & $py -3.11 --version
} catch {
    Write-Host "Python 3.11 não encontrado. Tentando Python 3.10..."
    & $py -3.10 --version
}

$version = "-3.11"
try {
    & $py $version --version | Out-Null
} catch {
    $version = "-3.10"
}

Write-Host "[2/4] Criando ambiente virtual..."
& $py $version -m venv .venv

Write-Host "[3/4] Instalando dependências..."
& ".\.venv\Scripts\python.exe" -m pip install --upgrade pip
& ".\.venv\Scripts\python.exe" -m pip install -r requirements.txt

Write-Host "[4/4] Instalando Chromium do Playwright..."
& ".\.venv\Scripts\python.exe" -m playwright install chromium

Write-Host ""
Write-Host "Instalação concluída."
Write-Host "Teste inicial: .\.venv\Scripts\python.exe run_experiment.py --smoke-test --mode extension --fresh"
