#!/usr/bin/env bash
set -e
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib.sh"

section_header "Setting up Traefik config..."
backup_and_link ~/www/traefik "$SCRIPTPATH/traefik"
echo_success "Traefik config done."
