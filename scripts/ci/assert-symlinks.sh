#!/usr/bin/env bash
# Asserts every symlink/file each scripts/install/*.sh section is supposed to
# create actually exists and points at the right repo path, plus that
# ~/.bashrc sources cleanly. Run this AFTER install.sh has executed against
# some $HOME - a throwaway one in a container, NEVER this machine's real
# $HOME (see .ai/plans/2026-09-02-install-ci-testing/PLAN.md's safety note).
#
# Usage: HOME=<throwaway home> scripts/ci/assert-symlinks.sh
#
# NOTE: for the ~/.bashrc check to pass, the repo must be reachable at
# $HOME/dotfiles - bashrc hardcodes that path in several places (bash/lib/colors,
# bash/.bash_aliases, backup-tools, bin, git/.git-completion.bash) regardless of
# where this script itself lives. Symlink or clone the repo to $HOME/dotfiles
# before running install.sh in a container - see RESULT.md for detail.

set -u

SCRIPTPATH="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

PASS=0
FAIL=0

check_symlink() {
  local target="$1" expected_source="$2" label="$3"
  local expected_real target_real

  if [ ! -L "$target" ]; then
    echo "FAIL: $label - $target is not a symlink"
    FAIL=$((FAIL + 1))
    return
  fi

  # -e follows the link, so this is the check that actually catches a link
  # pointing at nothing. The expected_real guard below cannot: readlink -f
  # canonicalises a missing *final* component rather than failing, so it only
  # ever fires when a parent directory is missing too.
  if [ ! -e "$target" ]; then
    echo "FAIL: $label - $target is a dangling symlink -> $(readlink "$target")"
    FAIL=$((FAIL + 1))
    return
  fi

  expected_real="$(readlink -f "$expected_source" 2>/dev/null)"
  target_real="$(readlink -f "$target" 2>/dev/null)"

  if [ -z "$expected_real" ]; then
    echo "FAIL: $label - expected source $expected_source does not resolve (missing from repo?)"
    FAIL=$((FAIL + 1))
    return
  fi

  if [ "$target_real" != "$expected_real" ]; then
    echo "FAIL: $label - $target resolves to $target_real, expected $expected_real"
    FAIL=$((FAIL + 1))
    return
  fi

  echo "PASS: $label"
  PASS=$((PASS + 1))
}

check_dir_exists() {
  local target="$1" label="$2"
  if [ -d "$target" ]; then
    echo "PASS: $label"
    PASS=$((PASS + 1))
  else
    echo "FAIL: $label - $target does not exist or is not a directory"
    FAIL=$((FAIL + 1))
  fi
}

echo "=== 10-bash.sh ==="
check_symlink ~/.bashrc "$SCRIPTPATH/bash/bashrc" "~/.bashrc -> bash/bashrc"
check_symlink ~/.dircolors "$SCRIPTPATH/bash/dircolors" "~/.dircolors -> bash/dircolors"

echo "=== 20-git.sh ==="
check_symlink ~/.gitconfig "$SCRIPTPATH/git/.gitconfig" "~/.gitconfig -> git/.gitconfig"

echo "=== 30-desktop-config.sh ==="
check_dir_exists ~/bin "~/bin exists"
for d in wireplumber waybar hypr fish; do
  check_symlink ~/.config/"$d" "$SCRIPTPATH/.config/$d" "~/.config/$d -> .config/$d"
done

echo "=== 40-systemd.sh ==="
check_symlink ~/.config/systemd "$SCRIPTPATH/.config/systemd" "~/.config/systemd -> .config/systemd"

echo "=== 50-ai-tools.sh ==="
check_symlink ~/AGENTS.md "$SCRIPTPATH/ai/AGENTS.md" "~/AGENTS.md -> ai/AGENTS.md"
for f in CLAUDE.md RTK.md settings.json statusline-command.sh; do
  check_symlink ~/.claude/"$f" "$SCRIPTPATH/ai/$f" "~/.claude/$f -> ai/$f"
done
for d in skills commands agents hooks lessons; do
  check_symlink ~/.claude/"$d" "$SCRIPTPATH/ai/$d" "~/.claude/$d -> ai/$d"
done

if command -v opencode >/dev/null 2>&1; then
  check_symlink ~/.config/opencode/agent "$SCRIPTPATH/ai/agents-opencode" "~/.config/opencode/agent -> ai/agents-opencode"
  check_symlink ~/.config/opencode/command "$SCRIPTPATH/ai/commands" "~/.config/opencode/command -> ai/commands"
  check_symlink ~/.config/opencode/skill "$SCRIPTPATH/ai/skills" "~/.config/opencode/skill -> ai/skills"
else
  echo "SKIP: opencode symlinks - opencode not installed in this environment"
fi

if command -v codex >/dev/null 2>&1; then
  for d in "$SCRIPTPATH"/ai/codex-skills/*/; do
    name="$(basename "$d")"
    check_symlink ~/.codex/skills/"$name" "$SCRIPTPATH/ai/codex-skills/$name" "~/.codex/skills/$name -> ai/codex-skills/$name"
  done
else
  echo "SKIP: codex skill symlinks - codex not installed in this environment"
fi

if command -v agy >/dev/null 2>&1; then
  check_symlink ~/.gemini/config/skills.json "$SCRIPTPATH/ai/gemini-config-skills.json" "~/.gemini/config/skills.json -> ai/gemini-config-skills.json"
else
  echo "SKIP: agy skills.json symlink - agy not installed in this environment"
fi

echo "=== 60-neovim.sh ==="
check_symlink ~/.config/nvim "$SCRIPTPATH/nvim" "~/.config/nvim -> nvim"

echo "=== 70-traefik.sh ==="
check_symlink ~/www/traefik "$SCRIPTPATH/traefik" "~/www/traefik -> traefik"

echo "=== ~/.bashrc sourcing ==="
if bash -c "source ~/.bashrc" >/dev/null 2>&1; then
  echo "PASS: ~/.bashrc sources without error"
  PASS=$((PASS + 1))
else
  echo "FAIL: ~/.bashrc did not source cleanly (see note at top of this script - repo must be reachable at \$HOME/dotfiles)"
  FAIL=$((FAIL + 1))
fi

echo
echo "=== Summary: $PASS passed, $FAIL failed ==="
[ "$FAIL" -eq 0 ]
