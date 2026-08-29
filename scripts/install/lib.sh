# vi: ft=bash
# Shared helpers for the dotfiles install scripts in this directory.
# Sourced, never executed directly.

DOTFILES_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SCRIPTPATH="$DOTFILES_ROOT"

source "$DOTFILES_ROOT/bash/lib/echos"

command_exists () {
  command -v "$1" >/dev/null 2>&1
}

# Backs up an existing non-symlink target to "<target>.old", then (re)links it.
# Safe to re-run: once the target is a symlink, this just repoints it.
# Usage: backup_and_link <target> <source>
backup_and_link () {
  local target="$1" source="$2"
  if [ -e "$target" ] && [ ! -L "$target" ]; then
    mv "$target" "$target.old"
  fi
  ln -sfn "$source" "$target"
}

section_header () {
  echo "------------------------------------"
  echo_info "$1"
}
