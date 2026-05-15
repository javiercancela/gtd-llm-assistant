#!/bin/bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SECRETS_FILE="${GTD_LLM_ASSISTANT_ENV:-$HOME/.config/gtd-llm-assistant/env}"

if [[ -f "$SECRETS_FILE" ]]; then
  set -a
  # shellcheck source=/dev/null
  source "$SECRETS_FILE"
  set +a
fi

exec "$REPO_ROOT/.venv/bin/python" "$REPO_ROOT/src/main.py"
