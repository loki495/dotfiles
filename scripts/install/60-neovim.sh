#!/usr/bin/env bash
set -e
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib.sh"

section_header "Neovim Application Installation"
if [ -n "$NVIM_INSTALL_CHOICE" ]; then
    nvim_choice="$NVIM_INSTALL_CHOICE"
    echo_info "Using NVIM_INSTALL_CHOICE=$nvim_choice (non-interactive)."
else
    echo "Do you want to install Neovim for the current user or globally?"
    echo "  1) User-local installation (\$HOME/.local/bin/nvim)"
    echo "  2) Global installation (/usr/local/bin/nvim - requires sudo)"
    read -rp "Please enter 1 or 2: " nvim_choice
fi

if [ "$nvim_choice" == "1" ]; then
    echo_info "Proceeding with user-local Neovim application installation."
    "$SCRIPTPATH/install_neovim.sh" --user
elif [ "$nvim_choice" == "2" ]; then
    echo_info "Proceeding with global Neovim application installation (will prompt for sudo password)."
    sudo "$SCRIPTPATH/install_neovim.sh" --global
else
    echo_info "Invalid choice or no choice made. Skipping Neovim application installation."
    echo_info "You can run '$SCRIPTPATH/install_neovim.sh --user' or 'sudo $SCRIPTPATH/install_neovim.sh --global' manually later."
fi

section_header "Neovim Configuration Link"
rm -rf ~/.config/nvim || true
ln -s "$SCRIPTPATH/nvim" ~/.config/nvim
echo_success "Neovim configuration linked to ~/.config/nvim."
