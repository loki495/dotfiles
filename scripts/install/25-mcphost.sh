#!/usr/bin/env bash
set -e
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib.sh"

section_header "Setting up .mcphost symlink..."
ln -sfn "$SCRIPTPATH/.mcphost" ~/.mcphost
echo_success ".mcphost done."
