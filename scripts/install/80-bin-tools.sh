#!/usr/bin/env bash
set -e
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib.sh"

# Fetches the dev-tool binaries this repo used to commit directly (~68 MB,
# mostly one 49 MB Go binary that's since been dropped entirely - see
# README's "bin/ - personal CLI utilities" section). rg and composer are
# official Arch packages; phpactor/phpbrew/phpcs/phpcbf are standalone phars
# with no pacman/AUR package, fetched straight from their GitHub releases.
# All land in ~/.local/bin (already on PATH via config.fish/bashrc), never
# into this repo's own bin/ - nothing here should hardcode a path into a
# git checkout for a tool that isn't actually part of this repo.
#
# Idempotent: skips anything already on PATH unless BIN_TOOLS_FORCE=1.

section_header "Installing rg and composer via pacman..."
sudo pacman -S --needed --noconfirm ripgrep composer
echo_success "ripgrep and composer installed."

mkdir -p "$HOME/.local/bin"

fetch_phar () {
  local name="$1" url="$2" target="$HOME/.local/bin/$name"
  if command_exists "$name" && [ -z "${BIN_TOOLS_FORCE:-}" ]; then
    echo_info "$name already on PATH ($(command -v "$name")), skipping. Set BIN_TOOLS_FORCE=1 to reinstall."
    return
  fi
  echo_info "Fetching $name..."
  curl -Ls -o "$target" "$url"
  chmod +x "$target"
  echo_success "$name installed to $target."
}

section_header "Installing phpactor (standalone phar)..."
# phpactor/phpactor releases/latest always resolves to the current release -
# no version to pin/update here.
fetch_phar phpactor "https://github.com/phpactor/phpactor/releases/latest/download/phpactor.phar"

section_header "Installing phpbrew (standalone phar)..."
fetch_phar phpbrew "https://github.com/phpbrew/phpbrew/releases/latest/download/phpbrew.phar"

section_header "Installing phpcs/phpcbf (PHP_CodeSniffer, standalone phars)..."
# squizlabs/PHP_CodeSniffer is abandoned - PHPCSStandards/PHP_CodeSniffer is
# the maintained successor (confirmed via the old repo's own README notice).
fetch_phar phpcs "https://github.com/PHPCSStandards/PHP_CodeSniffer/releases/latest/download/phpcs.phar"
fetch_phar phpcbf "https://github.com/PHPCSStandards/PHP_CodeSniffer/releases/latest/download/phpcbf.phar"

echo_success "bin-tools installed. phpactor/phpbrew/phpcs/phpcbf need php on PATH to run (they're phars)."
