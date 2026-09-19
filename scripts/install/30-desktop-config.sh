#!/usr/bin/env bash
set -e
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib.sh"

section_header "Desktop Environment Configuration Link"
# Use backup_and_link to safely symlink configs (it backs up instead of destroying)
for d in wireplumber waybar hypr fish; do
  backup_and_link ~/.config/"$d" "$SCRIPTPATH/.config/$d"
  echo_success "Linked ~/.config/$d"
done
