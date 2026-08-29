#!/usr/bin/env bash
set -e
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib.sh"

section_header "Setting up shared AGENTS.md entrypoint..."
backup_and_link ~/AGENTS.md "$SCRIPTPATH/ai/AGENTS.md"
echo_success "AGENTS.md linked (read natively by Codex and Antigravity's agy)."
