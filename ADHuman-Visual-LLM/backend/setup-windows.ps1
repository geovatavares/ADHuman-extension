$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

# Use the default runtime selected by py.exe. Missing optional runtimes are not
# probed, so Windows PowerShell cannot stop on "No suitable Python runtime".
$PythonExe = $null
$PythonVersion = $null
$ProbeCode = "import sys; print(sys.executable); print('.'.join(map(str, sys.version_info[:3]))); raise SystemExit(0 if sys.version_info >= (3, 10) else 1)"

if (Get-Command py -ErrorAction SilentlyContinue) {
    $SavedErrorActionPreference = $ErrorActionPreference
    $ErrorActionPreference = "SilentlyContinue"
    try {
        $Result = & py -c $ProbeCode 2>$null
        $ResultExitCode = $LASTEXITCODE
    } catch {
        $Result = $null
        $ResultExitCode = 1
    } finally {
        $ErrorActionPreference = $SavedErrorActionPreference
    }

    if ($ResultExitCode -eq 0 -and $Result) {
        $ResultLines = @($Result)
        if ($ResultLines.Count -ge 2) {
            $PythonExe = $ResultLines[$ResultLines.Count - 2].ToString().Trim()
            $PythonVersion = $ResultLines[$ResultLines.Count - 1].ToString().Trim()
        }
    }
}

if (-not $PythonExe -and (Get-Command python -ErrorAction SilentlyContinue)) {
    $SavedErrorActionPreference = $ErrorActionPreference
    $ErrorActionPreference = "SilentlyContinue"
    try {
        $Result = & python -c $ProbeCode 2>$null
        $ResultExitCode = $LASTEXITCODE
    } catch {
        $Result = $null
        $ResultExitCode = 1
    } finally {
        $ErrorActionPreference = $SavedErrorActionPreference
    }

    if ($ResultExitCode -eq 0 -and $Result) {
        $ResultLines = @($Result)
        if ($ResultLines.Count -ge 2) {
            $PythonExe = $ResultLines[$ResultLines.Count - 2].ToString().Trim()
            $PythonVersion = $ResultLines[$ResultLines.Count - 1].ToString().Trim()
        }
    }
}

if (-not $PythonExe) {
    Write-Host ""
    Write-Host "Nenhuma instalacao compativel do Python foi encontrada."
    Write-Host "Execute este comando para conferir as versoes instaladas: py -0p"
    Write-Host ""
    throw "Instale o Python 3.10 ou mais recente e deixe-o disponivel para py.exe ou no PATH."
}

Write-Host "Usando Python $PythonVersion"
Write-Host "Executavel: $PythonExe"

$VenvPython = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $VenvPython)) {
    Write-Host "Criando o ambiente virtual..."
    & $PythonExe -m venv .venv
    if ($LASTEXITCODE -ne 0) {
        throw "Nao foi possivel criar o ambiente virtual com o Python $PythonVersion."
    }
}

if (-not (Test-Path $VenvPython)) {
    throw "O ambiente virtual esta incompleto: .venv\Scripts\python.exe nao foi criado."
}

Write-Host "Atualizando o pip..."
& $VenvPython -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) {
    throw "Nao foi possivel atualizar o pip. Verifique a internet e tente novamente."
}

Write-Host "Instalando as dependencias do backend..."
& $VenvPython -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) {
    throw "Nao foi possivel instalar as dependencias do backend."
}

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
}

Write-Host ""
Write-Host "Backend instalado com sucesso usando Python $PythonVersion."
Write-Host "Agora execute 2-Iniciar-ADHuman-LLM.bat na pasta principal."
