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
# Every backup an install run makes goes under one timestamped directory, mirroring
# the target's path relative to $HOME. Section scripts inherit the run id from install.sh.
: "${DOTFILES_BACKUP_ROOT:=$HOME/.dotfiles-backups}"
: "${DOTFILES_BACKUP_RUN:=$(date +%Y%m%d-%H%M%S)}"
export DOTFILES_BACKUP_ROOT DOTFILES_BACKUP_RUN

same_content () {
  local a="$1" b="$2"
  if [ -L "$a" ] || [ -L "$b" ]; then
    [ -L "$a" ] && [ -L "$b" ] && [ "$(readlink -- "$a")" = "$(readlink -- "$b")" ]
  elif [ -d "$a" ] && [ -d "$b" ]; then
    diff -rq --no-dereference -- "$a" "$b" >/dev/null 2>&1
  elif [ -f "$a" ] && [ -f "$b" ]; then
    cmp -s -- "$a" "$b"
  else
    return 1
  fi
}

# Prints where to back up $1, or nothing when its exact content is already kept,
# either in the repo source $2 (may be empty) or in an earlier backup.
backup_path_for () {
  local target="$1" source="$2" relative candidate backup index=0
  if [ -n "$source" ] && same_content "$target" "$source"; then
    return 0
  fi
  case "$target" in
    "$HOME"/*) relative="${target#"$HOME"/}" ;;
    *) relative="_absolute$target" ;;
  esac
  for candidate in "$DOTFILES_BACKUP_ROOT"/*/"$relative" "$DOTFILES_BACKUP_ROOT"/*/"$relative".[0-9]*; do
    if { [ -e "$candidate" ] || [ -L "$candidate" ]; } && same_content "$target" "$candidate"; then
      return 0
    fi
  done
  backup="$DOTFILES_BACKUP_ROOT/$DOTFILES_BACKUP_RUN/$relative"
  while [ -e "$backup" ] || [ -L "$backup" ]; do
    index=$((index + 1))
    backup="$DOTFILES_BACKUP_ROOT/$DOTFILES_BACKUP_RUN/$relative.$index"
  done
  printf '%s\n' "$backup"
}

backup_and_link () {
  local target="$1" source="$2" backup="" parked="" previous
  mkdir -p "$(dirname "$target")" || return 1
  if [ -L "$target" ] && [ "$(readlink "$target")" = "$source" ]; then
    return 0
  fi
  if [ -e "$target" ] || [ -L "$target" ]; then
    backup=$(backup_path_for "$target" "$source") || return 1
    if [ -n "$backup" ]; then
      mkdir -p "$(dirname "$backup")" && mv -- "$target" "$backup" || return 1
      echo_info "Saved existing $target to $backup"
    else
      # Identical content is already kept; park it only until the link succeeds.
      parked=$(mktemp -u "$(dirname "$target")/.dotfiles-replaced.XXXXXX") || return 1
      mv -- "$target" "$parked" || return 1
    fi
  fi
  if ! ln -s -- "$source" "$target"; then
    echo_error "Could not link $target."
    previous="${backup:-$parked}"
    if [ -n "$previous" ]; then
      if [ ! -e "$target" ] && [ ! -L "$target" ] && mv -T -- "$previous" "$target"; then
        echo_info "Restored previous $target."
      else
        echo_error "Could not restore $target; previous contents remain at $previous."
      fi
    fi
    return 1
  fi
  if [ -n "$parked" ]; then
    rm -rf -- "$parked"
    echo_info "Replaced $target; an identical copy is already kept."
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
  local source="$1" target="$2" directory backup temporary
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
    backup=$(backup_path_for "$target" "") || return 1
    if [ -n "$backup" ]; then
      mkdir -p "$(dirname "$backup")" || return 1
      cp -a --no-dereference -- "$target" "$backup" || return 1
    fi
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
