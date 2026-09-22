#!/usr/bin/env bash
set -e
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib.sh"

section_header "Setting up BASH dotfiles..."
backup_and_link ~/.bashrc "$DOTFILES_ROOT/bash/bashrc"
echo_success "BASH dotfiles done."

section_header "Setting up dircolors..."
backup_and_link ~/.dircolors "$DOTFILES_ROOT/bash/dircolors"
echo_success "dircolors done."
