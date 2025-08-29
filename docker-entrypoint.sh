#!/usr/bin/env sh
set -e

CONFIG_PATH="/app/config.json"
: "${OVERWRITE_CONFIG:=true}"

if [ ! -f "$CONFIG_PATH" ] || [ "$OVERWRITE_CONFIG" = "true" ]; then
  echo "[entrypoint] Writing config to $CONFIG_PATH"
  cat > "$CONFIG_PATH" <<EOF
{
  "llm": {
    "api_key": "${LLM_API_KEY:-}",
    "base_url": "${LLM_BASE_URL:-https://api.openai.com/v1}",
    "model": "${LLM_MODEL:-gpt-3.5-turbo}",
    "temperature": ${LLM_TEMPERATURE:-0.7},
    "max_tokens": ${LLM_MAX_TOKENS:-20000},
    "timeout": ${LLM_TIMEOUT:-30}
  },
  "generation": {
    "default_difficulty": "${GEN_DEFAULT_DIFFICULTY:-medium}",
    "default_card_count": ${GEN_DEFAULT_CARD_COUNT:-1}
  },
  "export": {
    "default_formats": ["json", "apkg"],
    "output_directory": "${EXPORT_OUTPUT_DIR:-output}"
  },
  "templates": {
    "directory": "${TEMPLATES_DIR:-Card Template}"
  }
}
EOF
else
  echo "[entrypoint] Using existing config at $CONFIG_PATH"
fi

mkdir -p "/app/${EXPORT_OUTPUT_DIR:-output}" "/app/logs"

HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-5000}"
DEBUG_FLAG=""
if [ "${FLASK_DEBUG:-false}" = "true" ]; then
  DEBUG_FLAG="--debug"
fi

exec python -u main.py --web --host "$HOST" --port "$PORT" ${DEBUG_FLAG}
