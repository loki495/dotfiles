#!/usr/bin/env bash
set -e
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib.sh"

section_header "Setting up systemd user services..."
require_commands systemctl
if ! systemctl --user show-environment >/dev/null 2>&1; then
  echo_error "No systemd user session is available. Systemd setup is optional and was not changed."
  exit 1
fi
backup_and_link "$HOME/.config/systemd" "$DOTFILES_ROOT/.config/systemd"
systemctl --user daemon-reload
echo_success "systemd user services directory linked. Review wanted units before enabling any services."
