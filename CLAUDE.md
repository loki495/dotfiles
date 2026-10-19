# dotfiles

Delivery: direct push to `origin` (GitHub), after explicit push confirmation. Commit on the default branch.

Personal dotfiles (Hyprland/waybar desktop, Neovim, shell, PHP dev tooling, shared AI-agent
config). README.md is the reference; this file is the short version for agents.

- The global developer rules are `ai/CLAUDE.md`, already loaded as `~/.claude/CLAUDE.md`;
  don't duplicate them here.
- Files here are symlinked into `$HOME`, so editing the repo copy changes the live config at
  once. Never edit only the live copy.
- Public repo: anything naming real hosts, IPs, domains or tokens goes in `~/.dotfiles-private`.
- Branches: `master` is the default; `old-laptop` is an archive, leave it alone.
- Installer sections are `scripts/install/NN-name.sh`; each must be rerunnable and use
  `backup_and_link`.
- Tests: `python3 tests/test_backup_tools.py` runs on the host. `tests/test_installers.py` and
  `scripts/ci/test-install.sh` write into `$HOME` and must run in a throwaway container (README,
  "Tests"). Never run them on the real machine.
- Docs and tests ship in the same commit as the change.
