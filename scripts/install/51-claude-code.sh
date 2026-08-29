#!/usr/bin/env bash
set -e
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib.sh"

section_header "Setting up Claude Code config..."
mkdir -p ~/.claude
for f in CLAUDE.md RTK.md settings.json statusline-command.sh; do
  rm -f ~/.claude/"$f"
  ln -s "$SCRIPTPATH/ai/$f" ~/.claude/"$f"
done
for d in skills commands agents hooks; do
  rm -rf ~/.claude/"$d"
  ln -s "$SCRIPTPATH/ai/$d" ~/.claude/"$d"
done
echo_success "Claude Code config linked to ~/.claude."
echo_info "  - Uses this machine's username in ~/.claude/settings.json's hook paths (/home/andres/...) —"
echo_info "    if provisioning under a different username, update those paths after linking."
