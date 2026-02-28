#!/usr/bin/env bash
set -euo pipefail

# Example:
#   export SGLANG_MODEL_PATH="Qwen/Qwen2.5-Coder-7B-Instruct"
#   export SGLANG_HOST="0.0.0.0"
#   export SGLANG_PORT="30000"
#   ./scripts/run_sglang_server.sh

SGLANG_MODEL_PATH="${SGLANG_MODEL_PATH:-Qwen/Qwen2.5-Coder-7B-Instruct}"
SGLANG_HOST="${SGLANG_HOST:-0.0.0.0}"
SGLANG_PORT="${SGLANG_PORT:-30000}"

python3 -m sglang.launch_server \
  --model-path "${SGLANG_MODEL_PATH}" \
  --host "${SGLANG_HOST}" \
  --port "${SGLANG_PORT}"
