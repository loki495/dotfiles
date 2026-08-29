#!/usr/bin/env bash
set -e
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib.sh"

section_header "Setting up opencode config..."
if ! command_exists opencode; then
  echo_info "opencode not found on this machine, skipping."
  exit 0
fi

mkdir -p ~/.config/opencode
ln -sfn "$SCRIPTPATH/ai/agents-opencode" ~/.config/opencode/agent
ln -sfn "$SCRIPTPATH/ai/commands" ~/.config/opencode/command
ln -sfn "$SCRIPTPATH/ai/skills" ~/.config/opencode/skill
echo_success "opencode agent/command/skill dirs linked to shared ai/ config."
echo_info "  - opencode.jsonc's own \"instructions\" field must point at ~/.claude/CLAUDE.md;"
echo_info "    this section only wires the agent/command/skill directories."
