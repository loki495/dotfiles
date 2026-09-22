# shellcheck shell=bash
# vi: ft=bash
# Shared helpers for the dotfiles install scripts in this directory.
# Sourced, never executed directly.

DOTFILES_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

source "$DOTFILES_ROOT/bash/lib/echos"

command_exists () {
  command -v "$1" >/dev/null 2>&1
}

# Preserve every displaced target, including custom or dangling symlinks.
backup_and_link () {
  local target="$1" source="$2" backup="" index=0
  mkdir -p "$(dirname "$target")" || return 1
  if [ -L "$target" ] && [ "$(readlink "$target")" = "$source" ]; then
    return 0
  fi
  if [ -e "$target" ] || [ -L "$target" ]; then
    backup="$target.old"
    while [ -e "$backup" ] || [ -L "$backup" ]; do
      index=$((index + 1))
      backup="$target.old.$index"
    done
    mv -- "$target" "$backup" || return 1
    echo_info "Saved existing $target to $backup"
  fi
  if ! ln -s -- "$source" "$target"; then
    echo_error "Could not link $target."
    if [ -n "$backup" ]; then
      if [ ! -e "$target" ] && [ ! -L "$target" ] && mv -T -- "$backup" "$target"; then
        echo_info "Restored previous $target."
      else
        echo_error "Could not restore $target; previous contents remain at $backup."
      fi
    fi
    return 1
  fi
}

require_commands () {
  local command
  for command in "$@"; do
    if ! command_exists "$command"; then
      echo_error "Required command '$command' is missing. Install it and retry."
      return 1
    fi
  done
}

# Keep backups outside parser/queries globs and publish changed files atomically.
install_managed_file () (
  set -e
  local source="$1" target="$2" directory backup index=0 temporary
  directory=$(dirname "$target")
  mkdir -p "$directory" || return 1
  if [ -f "$target" ] && [ ! -L "$target" ] && cmp -s -- "$source" "$target"; then
    return 0
  fi
  if [ -d "$target" ] && [ ! -L "$target" ]; then
    echo_error "Refusing to replace directory with a file: $target"
    return 1
  fi
  temporary=$(mktemp "$directory/.install.XXXXXX") || return 1
  trap 'rm -f -- "$temporary"' EXIT
  cp --preserve=mode -- "$source" "$temporary" || return 1
  if [ -e "$target" ] || [ -L "$target" ]; then
    mkdir -p "$directory/.dotfiles-backups" || return 1
    backup="$directory/.dotfiles-backups/$(basename "$target").old"
    while [ -e "$backup" ] || [ -L "$backup" ]; do
      index=$((index + 1))
      backup="$directory/.dotfiles-backups/$(basename "$target").old.$index"
    done
    cp -a --no-dereference -- "$target" "$backup" || return 1
  fi
  mv -fT -- "$temporary" "$target"
)

# Download alongside the destination, so a failure never truncates a working tool.
download_executable () (
  set -e
  local url="$1" target="$2" temporary
  require_commands curl mktemp chmod mv
  mkdir -p "$(dirname "$target")"
  temporary=$(mktemp "$(dirname "$target")/.download.XXXXXX")
  trap 'rm -f -- "$temporary"' EXIT
  curl --fail --location --show-error --silent --output "$temporary" "$url"
  if [ ! -s "$temporary" ]; then
    echo_error "Download was empty: $url"
    return 1
  fi
  chmod +x "$temporary"
  install_managed_file "$temporary" "$target"
)

section_header () {
  echo "------------------------------------"
  echo_info "$1"
}
