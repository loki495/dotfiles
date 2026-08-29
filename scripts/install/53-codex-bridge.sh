#!/usr/bin/env bash
set -e
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib.sh"

section_header "Setting up Codex skill-import bridge..."
if ! command_exists codex; then
  echo_info "codex not found on this machine, skipping."
  exit 0
fi

mkdir -p ~/.codex/skills
for d in "$SCRIPTPATH"/ai/codex-skills/*/; do
  name=$(basename "$d")
  ln -sfn "$SCRIPTPATH/ai/codex-skills/$name" ~/.codex/skills/"$name"
done
echo_success "Codex claude-import-* skill wrappers linked to shared ai/ config."
