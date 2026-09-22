#!/usr/bin/env bash
set -e
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib.sh"

section_header "Setting up shared AGENTS.md entrypoint..."
backup_and_link ~/AGENTS.md "$DOTFILES_ROOT/ai/AGENTS.md"
echo_success "AGENTS.md linked (read natively by Codex and Antigravity's agy)."

section_header "Setting up Claude Code config..."
mkdir -p ~/.claude
for f in CLAUDE.md RTK.md settings.json statusline-command.sh; do
  backup_and_link ~/.claude/"$f" "$DOTFILES_ROOT/ai/$f"
done
for d in skills commands agents hooks lessons; do
  backup_and_link ~/.claude/"$d" "$DOTFILES_ROOT/ai/$d"
done
echo_success "Claude Code config linked to ~/.claude."
echo_info "  - settings.json's hook commands use \$HOME, portable to any username. Personal"
echo_info "    hooks (referencing a separate sessioneer checkout) live in"
echo_info "    ~/.claude/settings.local.json instead — not linked from this repo."

section_header "Setting up opencode config..."
if command_exists opencode; then
  mkdir -p ~/.config/opencode
  backup_and_link ~/.config/opencode/agent "$DOTFILES_ROOT/ai/agents-opencode"
  backup_and_link ~/.config/opencode/command "$DOTFILES_ROOT/ai/commands"
  backup_and_link ~/.config/opencode/skill "$DOTFILES_ROOT/ai/skills"
  echo_success "opencode agent/command/skill directories linked."
  echo_info "Service startup is optional: run ./install.sh systemd, then explicitly enable opencode-serve.service if wanted."
  echo_info "  - opencode.jsonc's own \"instructions\" field must point at ~/.claude/CLAUDE.md;"
  echo_info "    this section only wires the agent/command/skill directories and the server."
else
  echo_info "opencode not found on this machine, skipping."
fi

section_header "Setting up Codex skill-import bridge..."
if command_exists codex; then
  mkdir -p ~/.codex/skills
  for d in "$DOTFILES_ROOT"/ai/codex-skills/*/; do
    name=$(basename "$d")
    backup_and_link ~/.codex/skills/"$name" "$DOTFILES_ROOT/ai/codex-skills/$name"
  done
  echo_success "Codex claude-import-* skill wrappers linked to shared ai/ config."
else
  echo_info "codex not found on this machine, skipping."
fi

section_header "Setting up Antigravity (agy) skills config..."
if command_exists agy; then
  mkdir -p ~/.gemini/config
  backup_and_link ~/.gemini/config/skills.json "$DOTFILES_ROOT/ai/gemini-config-skills.json"
  echo_success "agy skills.json linked (points agy's global skill discovery at ai/skills)."
else
  echo_info "agy not found on this machine, skipping."
fi
