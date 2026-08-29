#!/usr/bin/env bash
set -e
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib.sh"

section_header "Setting up Antigravity (agy) skills config..."
if ! command_exists agy; then
  echo_info "agy not found on this machine, skipping."
  exit 0
fi

mkdir -p ~/.gemini/config
backup_and_link ~/.gemini/config/skills.json "$SCRIPTPATH/ai/gemini-config-skills.json"
echo_success "agy skills.json linked (points agy's global skill discovery at ai/skills)."
