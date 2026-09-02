#!/usr/bin/env bash
# Driver: runs the whole "does the dotfiles install actually work" suite for
# real - install.sh, then install_neovim.sh --parsers/--queries, then
# assert-symlinks.sh and test-nvim-highlighting.sh - inside whatever $HOME
# this process has.
#
# NEVER point this at a real dev machine's actual $HOME - install.sh creates/
# overwrites ~/.bashrc, ~/.gitconfig, ~/.config/systemd, ~/.config/nvim,
# ~/.claude, etc for real, and runs systemctl --user daemon-reload. See
# .ai/plans/2026-09-02-install-ci-testing/PLAN.md's CRITICAL SAFETY CONSTRAINT.
#
# Required: DOTFILES_CI_TEST=1 set explicitly by the caller (the CI workflow,
# or a documented local `docker run` wrapper) - refuses to run otherwise, so
# this can't accidentally fire against a real machine.
#
# Expects:
#   - this repo checked out at exactly $HOME/dotfiles (bash/bashrc hardcodes
#     that path unconditionally - see RESULT.md's T2 finding)
#   - scripts/ci/stubs/ already prepended to PATH (systemctl no-op - see T3),
#     so 40-systemd.sh's daemon-reload doesn't fail without a real user
#     systemd session
#   - tree-sitter-cli, git, npm/node, a C compiler, tmux already installed
#     (install_neovim.sh --parsers needs all of these; see T6's workflow for
#     the actual package list)
#
# Usage: DOTFILES_CI_TEST=1 scripts/ci/test-install.sh

set -uo pipefail

if [ "${DOTFILES_CI_TEST:-}" != "1" ]; then
    echo "FATAL: refusing to run - set DOTFILES_CI_TEST=1 explicitly to confirm" >&2
    echo "this is running against a throwaway/isolated \$HOME, never a real one." >&2
    exit 1
fi

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

if [ "$REPO_ROOT" != "$HOME/dotfiles" ]; then
    echo "FATAL: repo must be checked out at exactly \$HOME/dotfiles" >&2
    echo "  got: $REPO_ROOT" >&2
    echo "  HOME=$HOME" >&2
    echo "bash/bashrc hardcodes ~/dotfiles/... paths - see RESULT.md's T2 entry." >&2
    exit 1
fi

fail() {
    echo "" >&2
    echo "=== FAILED: $1 ===" >&2
    exit 1
}

echo "=== [1/6] install.sh (all sections, non-interactive nvim choice) ==="
NVIM_INSTALL_CHOICE=1 "$REPO_ROOT/install.sh" || fail "install.sh"

# install_neovim.sh --user puts the nvim binary at $HOME/.local/bin/nvim but
# never modifies PATH itself (it just prints a reminder) - export it now so
# every later step in this script (and test-nvim-highlighting.sh, which
# shells out to `nvim` via tmux) can actually find it.
export PATH="$HOME/.local/bin:$PATH"

# git/.gitconfig (symlinked to ~/.gitconfig by 20-git.sh, just installed by
# the install.sh step above) rewrites every plain https://github.com/ clone
# to SSH via `[url "git@github.com:"] insteadOf = https://github.com/`. That's
# fine on a real dev machine with SSH keys set up, but there's no SSH agent in
# a throwaway CI container, so it breaks every clone install_neovim.sh
# --parsers/--queries does below. GIT_CONFIG_GLOBAL=/dev/null tells git to
# skip the normal global-config lookup entirely for the rest of this script -
# confirmed this bypasses the rewrite without touching the actual repo file
# (unlike `git config --global --unset`, which would edit the file THROUGH
# the symlink and mutate the real tracked git/.gitconfig).
export GIT_CONFIG_GLOBAL=/dev/null

if ! command -v nvim >/dev/null 2>&1; then
    fail "nvim not found on PATH after install.sh (expected at \$HOME/.local/bin/nvim)"
fi
echo "nvim resolved to: $(command -v nvim) ($(nvim --version | head -1))"

echo "=== [2/6] assert-symlinks.sh ==="
"$REPO_ROOT/scripts/ci/assert-symlinks.sh" || fail "assert-symlinks.sh"

echo "=== [3/6] install_neovim.sh --parsers (full language set) ==="
"$REPO_ROOT/install_neovim.sh" --parsers || fail "install_neovim.sh --parsers"

echo "=== [4/6] install_neovim.sh --queries (full language set) ==="
"$REPO_ROOT/install_neovim.sh" --queries || fail "install_neovim.sh --queries"

echo "=== [5/6] bootstrap lazy.nvim plugins (fresh nvim data dir needs this once) ==="
# On a real dev machine this is already done from prior usage, so it's easy to
# forget - but a genuinely fresh $HOME (any container, including CI) has never
# launched nvim before, and lazy.nvim needs an explicit sync to install AND
# build every plugin (native compile steps included, e.g. telescope-fzf-
# native's .so) before anything depending on them works. Confirmed: without
# this, 6/11 languages in the highlighting check below failed - not because of
# missing parsers, but because a hard Lua error partway through plugin loading
# (telescope-fzf-native's uncompiled binary) interrupted nvim's startup before
# autocmds.lua's FileType autocmd got registered for some filetypes, depending
# on plugin load order. Adding this step alone took the failures to 0/11.
timeout 180 nvim --headless "+Lazy! sync" +qa || fail "Lazy! sync (plugin bootstrap)"

echo "=== [6/6] nvim highlighting check (tmux-based, all languages) ==="
"$REPO_ROOT/scripts/ci/test-nvim-highlighting.sh" || fail "test-nvim-highlighting.sh"

echo ""
echo "=== ALL CHECKS PASSED ==="
