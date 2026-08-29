#!/usr/bin/env bash
set -e
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib.sh"

section_header "Neovim Configuration Link"
rm -rf ~/.config/nvim || true
ln -s "$SCRIPTPATH/nvim" ~/.config/nvim
echo_success "Neovim configuration linked to ~/.config/nvim."
