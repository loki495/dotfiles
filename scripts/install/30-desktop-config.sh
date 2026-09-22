#!/usr/bin/env bash
set -e
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib.sh"

section_header "Ensuring ~/bin exists (on PATH via bashrc/fish)..."
mkdir -p ~/bin

section_header "Desktop Environment Configuration Link"
# Ensure .config directory exists before creating symlinks
mkdir -p ~/.config

# Use backup_and_link to safely symlink configs (it backs up instead of destroying)
for d in wireplumber waybar hypr fish; do
  backup_and_link ~/.config/"$d" "$DOTFILES_ROOT/.config/$d"
  echo_success "Linked ~/.config/$d"
done
