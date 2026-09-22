#!/usr/bin/env bash
set -e
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib.sh"

section_header "Neovim Application Installation"
nvim_options=()
case "${NVIM_LEGACY:-0}" in
    0) ;;
    1) nvim_options+=(--legacy) ;;
    *) echo_error "NVIM_LEGACY must be 0 or 1."; exit 1 ;;
esac
case "${NVIM_SOURCE:-0}" in
    0) ;;
    1) nvim_options+=(--source) ;;
    *) echo_error "NVIM_SOURCE must be 0 or 1."; exit 1 ;;
esac
if [ -n "${NVIM_INSTALL_CHOICE:-}" ]; then
    nvim_choice="${NVIM_INSTALL_CHOICE:-}"
    echo_info "Using NVIM_INSTALL_CHOICE=$nvim_choice (non-interactive)."
else
    echo "Do you want to install Neovim for the current user or globally?"
    echo "  1) User-local installation (\$HOME/.local/bin/nvim)"
    echo "  2) Global installation (/usr/local/bin/nvim - requires sudo)"
    if ! read -rp "Please enter 1 or 2: " nvim_choice; then
        echo_error "No installation choice supplied. Set NVIM_INSTALL_CHOICE=1 (user) or 2 (global)."
        exit 1
    fi
fi

if [ "$nvim_choice" == "1" ]; then
    echo_info "Proceeding with user-local Neovim application installation."
    "$DOTFILES_ROOT/install_neovim.sh" --user "${nvim_options[@]}"
elif [ "$nvim_choice" == "2" ]; then
    echo_info "Proceeding with global Neovim application installation (will prompt for sudo password)."
    sudo "$DOTFILES_ROOT/install_neovim.sh" --global "${nvim_options[@]}"
else
    echo_error "Invalid Neovim installation choice: $nvim_choice (expected 1 or 2)."
    echo_info "You can run '$DOTFILES_ROOT/install_neovim.sh --user' or 'sudo $DOTFILES_ROOT/install_neovim.sh --global' manually later."
    exit 1
fi

section_header "Neovim Configuration Link"
# Use backup_and_link instead of destructive rm -rf
backup_and_link ~/.config/nvim "$DOTFILES_ROOT/nvim"
echo_success "Neovim configuration linked to ~/.config/nvim (existing configs are backed up without overwriting earlier backups)."
