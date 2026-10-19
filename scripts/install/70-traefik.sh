#!/usr/bin/env bash
set -e
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib.sh"

section_header "Setting up Traefik config..."
# The config lives in the private repo, so there is nothing to link without it.
PRIVATE_ROOT="${DOTFILES_PRIVATE_ROOT:-$HOME/.dotfiles-private}"
if [ ! -d "$PRIVATE_ROOT/traefik" ]; then
  echo_error "No Traefik config at $PRIVATE_ROOT/traefik; not changed."
  exit 1
fi
# Unlike every other backup_and_link target here (~/.bashrc, ~/.gitconfig -
# straight in $HOME), this one nests under ~/www/, which a fresh machine
# (or this repo's own CI, which install.sh runs against a clean container)
# has no reason to already have.
mkdir -p ~/www
backup_and_link ~/www/traefik "$PRIVATE_ROOT/traefik"
echo_success "Traefik config done."
