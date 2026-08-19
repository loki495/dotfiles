#!/usr/bin/env bash
# boost-query.sh
# Wrapper for MCPHost + Laravel Boost MCP + Ollama models

# ----------------------------
# CONFIGURATION
# ----------------------------

#DEFAULT_MODEL="ollama:qwen3:4b"
#DEFAULT_MODEL="ollama:gemma:7b"
DEFAULT_MODEL="ollama:llama3.2"

# Check if first argument is a model (format: provider:model)
if [[ "$1" =~ ^[a-zA-Z0-9_]+:[a-zA-Z0-9_\-]+(:[a-zA-Z0-9_\-]+)?$ ]]; then
    MODEL="$1"
    shift
else
    MODEL="$DEFAULT_MODEL"
fi

# The rest of the arguments are the prompt
PROMPT="$*"⏎

#set -x 
# ----------------------------
# VALIDATION
# ----------------------------
CLAUDE_FILE="$PWD/CLAUDE.md"
if [ ! -f "$CLAUDE_FILE" ]; then
  echo "Warning: CLAUDE.md not found at $CLAUDE_FILE, proceeding without system prompt."
  SYSTEM_PROMPT_ARG=""
else
  SYSTEM_PROMPT_ARG="--system-prompt $CLAUDE_FILE"
fi

# ----------------------------
# RUN MCPHost
# ----------------------------
~/dotfiles/bin/mcphost \
  -m "$MODEL" \
  $SYSTEM_PROMPT_ARG \
  -p "$PROMPT" \
  --stream \
  --debug

