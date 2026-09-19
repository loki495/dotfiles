#!/usr/bin/env bash
set -e
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib.sh"

section_header "AI Tools Configuration"
for d in claude opencode; do
  if [ -d "$SCRIPTPATH/ai/$d" ]; then
    backup_and_link ~/.claude/"$d" "$SCRIPTPATH/ai/$d"
    echo_success "Linked ~/.claude/$d"
  fi
done
