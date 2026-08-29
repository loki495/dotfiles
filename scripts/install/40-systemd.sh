#!/usr/bin/env bash
set -e
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib.sh"

section_header "Setting up systemd user services..."
if [ -e ~/.config/systemd ] && [ ! -L ~/.config/systemd ]; then
  mv ~/.config/systemd ~/.config/systemd.old
fi
ln -sfn "$SCRIPTPATH/.config/systemd" ~/.config/systemd
systemctl --user daemon-reload
echo_success "systemd user services directory linked."
