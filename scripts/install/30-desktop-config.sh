#!/usr/bin/env bash
set -e
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib.sh"

section_header "Ensuring ~/bin exists (on PATH via bashrc/fish)..."
mkdir -p ~/bin

section_header "Setting up .config symlinks (Garuda/Hyprland desktop)..."
mkdir -p ~/.config
for d in wireplumber waybar hypr fish; do
  rm -rf ~/.config/"$d" || true
  ln -s "$SCRIPTPATH/.config/$d" ~/.config/"$d"
done
echo_success ".config symlinks done."
