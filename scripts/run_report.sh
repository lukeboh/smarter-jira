#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"
VENV_DIR="${VENV_DIR:-${ROOT_DIR}/.venv}"
REQ_FILE="${REQ_FILE:-${ROOT_DIR}/requirements.txt}"

fail() {
  echo "Erro: $1" >&2
  exit 1
}

command -v "$PYTHON_BIN" >/dev/null 2>&1 || fail "Python não encontrado. Instale Python >=3.10 e garanta 'python3' no PATH."

if ! "$PYTHON_BIN" - <<'PY'
import sys
sys.exit(0 if sys.version_info >= (3, 10) else 1)
PY
then
  fail "Versão do Python incompatível. Requer >=3.10."
fi

if [ ! -d "$VENV_DIR" ]; then
  echo "Criando venv em $VENV_DIR..."
  "$PYTHON_BIN" -m venv "$VENV_DIR" || fail "Falha ao criar venv."
  echo "Instalando dependências..."
  "$VENV_DIR/bin/pip" install -r "$REQ_FILE" || fail "Falha ao instalar dependências."
fi

if [ ! -x "$VENV_DIR/bin/python" ]; then
  fail "Python do venv não encontrado em $VENV_DIR/bin/python. Remova o venv e tente novamente."
fi

cd "$ROOT_DIR"
exec "$VENV_DIR/bin/python" "report.py" "$@"
