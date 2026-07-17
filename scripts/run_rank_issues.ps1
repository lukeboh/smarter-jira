# scripts/run_rank_issues.ps1
$ROOT_DIR = Resolve-Path "$PSScriptRoot\.."
$PYTHON_BIN = "python"

# Tenta detectar se o comando 'python' funciona, caso contrário tenta 'python3'
try {
    $null = & python --version 2>$null
} catch {
    $PYTHON_BIN = "python3"
}

# Verificar se a variável de ambiente PYTHON_BIN já está definida
if ($env:PYTHON_BIN) {
    $PYTHON_BIN = $env:PYTHON_BIN
}

$VENV_DIR = if ($env:VENV_DIR) { $env:VENV_DIR } else { "$ROOT_DIR\.venv" }
$REQ_FILE = if ($env:REQ_FILE) { $env:REQ_FILE } else { "$ROOT_DIR\requirements.txt" }

# Verificar se o interpretador Python está disponível e é versão >= 3.10
try {
    $versionCheck = & $PYTHON_BIN -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Python versão inferior a 3.10. O Smarter Jira requer Python >= 3.10."
        exit 1
    }
} catch {
    Write-Error "Python não encontrado. Instale o Python >= 3.10 e certifique-se de que ele está adicionado ao PATH do seu sistema."
    exit 1
}

# Criar o ambiente virtual se não existir
if (-not (Test-Path $VENV_DIR)) {
    Write-Host "Criando ambiente virtual (.venv) em $VENV_DIR..."
    & $PYTHON_BIN -m venv $VENV_DIR
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Falha ao criar o ambiente virtual."
        exit 1
    }
    
    # Atualizar o pip e instalar as dependências
    Write-Host "Instalando dependências de $REQ_FILE..."
    & "$VENV_DIR\Scripts\pip.exe" install --upgrade pip
    & "$VENV_DIR\Scripts\pip.exe" install -r $REQ_FILE
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Falha ao instalar as dependências."
        exit 1
    }
}

$VENV_PYTHON = "$VENV_DIR\Scripts\python.exe"
if (-not (Test-Path $VENV_PYTHON)) {
    Write-Error "Python do venv não encontrado em $VENV_PYTHON. Por favor, remova a pasta '.venv' e execute novamente."
    exit 1
}

# Executa o script python com todos os parâmetros fornecidos
Set-Location $ROOT_DIR
& $VENV_PYTHON rank_issues.py $args
