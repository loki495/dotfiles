#!/usr/bin/env bash
set -e
# Thin entrypoint for the dotfiles install. Runs every section in
# scripts/install/ in order, or just the sections named on the command line.
#
# Usage:
#   ./install.sh                       # run everything
#   ./install.sh bash git              # run only these sections
#   ./install.sh --list                # list available sections
#
# Each section is also independently runnable directly, e.g.:
#   ./scripts/install/51-claude-code.sh

SCRIPTPATH="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
INSTALL_DIR="$SCRIPTPATH/scripts/install"

source "$INSTALL_DIR/lib.sh"

list_sections () {
  for f in "$INSTALL_DIR"/[0-9][0-9]-*.sh; do
    name=$(basename "$f")
    name=${name#[0-9][0-9]-}
    name=${name%.sh}
    echo "$name"
  done
}

usage () {
  echo "Usage: $0 [section...] | --list | --help"
  echo
  echo "Available sections:"
  list_sections | sed 's/^/  /'
}

if [ "$1" == "-h" ] || [ "$1" == "--help" ]; then
  usage
  exit 0
fi

if [ "$1" == "--list" ]; then
  list_sections
  exit 0
fi

echo_info "Checking for required commands..."
REQUIRED_COMMANDS=("readlink" "dirname" "mv" "ln" "curl" "wget" "tar" "mkdir" "rm")
for cmd in "${REQUIRED_COMMANDS[@]}"; do
  if ! command_exists "$cmd"; then
    echo_error "Error: Required command '$cmd' is not installed. Please install it and try again."
    exit 1
  fi
done
echo_success "All required commands found."

REQUESTED=("$@")

if [ ${#REQUESTED[@]} -gt 0 ]; then
  AVAILABLE=$(list_sections)
  for want in "${REQUESTED[@]}"; do
    if ! grep -qx "$want" <<< "$AVAILABLE"; then
      echo_error "Unknown section: $want"
      usage
      exit 1
    fi
  done
fi

for script in "$INSTALL_DIR"/[0-9][0-9]-*.sh; do
  name=$(basename "$script")
  name=${name#[0-9][0-9]-}
  name=${name%.sh}

  if [ ${#REQUESTED[@]} -gt 0 ]; then
    skip=1
    for want in "${REQUESTED[@]}"; do
      [ "$want" == "$name" ] && skip=0 && break
    done
    [ "$skip" -eq 1 ] && continue
  fi

  source "$script"
done

echo
echo "===================================="
echo "Dotfiles setup complete!"
echo "Remember to:"
echo "  - Ensure '\$HOME/.local/bin' is in your PATH if you chose user-local Neovim installation."
echo "===================================="
