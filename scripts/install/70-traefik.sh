#!/usr/bin/env bash
set -e
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib.sh"

section_header "Setting up Traefik config..."
# Unlike every other backup_and_link target here (~/.bashrc, ~/.gitconfig -
# straight in $HOME), this one nests under ~/www/, which a fresh machine
# (or this repo's own CI, which install.sh runs against a clean container)
# has no reason to already have.
mkdir -p ~/www
backup_and_link ~/www/traefik "$SCRIPTPATH/traefik"
echo_success "Traefik config done."
