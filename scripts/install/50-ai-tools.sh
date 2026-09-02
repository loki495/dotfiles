#!/usr/bin/env bash
set -e
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib.sh"

section_header "Setting up shared AGENTS.md entrypoint..."
backup_and_link ~/AGENTS.md "$SCRIPTPATH/ai/AGENTS.md"
echo_success "AGENTS.md linked (read natively by Codex and Antigravity's agy)."

section_header "Setting up .mcphost symlink..."
ln -sfn "$SCRIPTPATH/.mcphost" ~/.mcphost
echo_success ".mcphost done."

section_header "Setting up Claude Code config..."
mkdir -p ~/.claude
for f in CLAUDE.md RTK.md settings.json statusline-command.sh; do
  rm -f ~/.claude/"$f"
  ln -s "$SCRIPTPATH/ai/$f" ~/.claude/"$f"
done
for d in skills commands agents hooks lessons; do
  rm -rf ~/.claude/"$d"
  ln -s "$SCRIPTPATH/ai/$d" ~/.claude/"$d"
done
echo_success "Claude Code config linked to ~/.claude."
echo_info "  - Uses this machine's username in ~/.claude/settings.json's hook paths (/home/andres/...) —"
echo_info "    if provisioning under a different username, update those paths after linking."

section_header "Setting up opencode config..."
if command_exists opencode; then
  mkdir -p ~/.config/opencode
  ln -sfn "$SCRIPTPATH/ai/agents-opencode" ~/.config/opencode/agent
  ln -sfn "$SCRIPTPATH/ai/commands" ~/.config/opencode/command
  ln -sfn "$SCRIPTPATH/ai/skills" ~/.config/opencode/skill
  systemctl --user daemon-reload
  systemctl --user enable --now opencode-serve.service
  echo_success "opencode agent/command/skill dirs linked and opencode-serve enabled."
  echo_info "  - opencode.jsonc's own \"instructions\" field must point at ~/.claude/CLAUDE.md;"
  echo_info "    this section only wires the agent/command/skill directories and the server."
else
  echo_info "opencode not found on this machine, skipping."
fi

section_header "Setting up Codex skill-import bridge..."
if command_exists codex; then
  mkdir -p ~/.codex/skills
  for d in "$SCRIPTPATH"/ai/codex-skills/*/; do
    name=$(basename "$d")
    ln -sfn "$SCRIPTPATH/ai/codex-skills/$name" ~/.codex/skills/"$name"
  done
  echo_success "Codex claude-import-* skill wrappers linked to shared ai/ config."
else
  echo_info "codex not found on this machine, skipping."
fi

section_header "Setting up Antigravity (agy) skills config..."
if command_exists agy; then
  mkdir -p ~/.gemini/config
  backup_and_link ~/.gemini/config/skills.json "$SCRIPTPATH/ai/gemini-config-skills.json"
  echo_success "agy skills.json linked (points agy's global skill discovery at ai/skills)."
else
  echo_info "agy not found on this machine, skipping."
fi
