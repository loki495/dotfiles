#!/usr/bin/env bash
set -e
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib.sh"

section_header "Setting up GIT dotfiles..."
backup_and_link ~/.gitconfig "$DOTFILES_ROOT/git/.gitconfig"
echo_success "GIT dotfiles done."
