# Contributing

This is a personal dotfiles repo, public so it can be read and borrowed from. Issues and
pull requests are welcome, but it is tuned to one machine and I may decline changes that
don't fit it.

## Before you open a PR

- Read the README's Installation and Tests sections. The repo must live at `~/dotfiles`
  (several configs hardcode that path).
- Run the tests that apply:
  - `python3 tests/test_backup_tools.py` (host-safe)
  - `tests/test_installers.py` and `scripts/ci/test-install.sh` write into `$HOME`, so they
    refuse to run outside a throwaway container. The README shows the exact `docker run`.
- Keep docs and tests in the same commit as the change they describe.
- Installer sections in `scripts/install/` must stay rerunnable and back up what they
  replace (`backup_and_link` in `scripts/install/lib.sh`).
- Never commit tokens, hostnames, IPs or domains of private infrastructure. Those belong in a
  separate private repo (see README, "Private dotfiles").

## Commits

One concern per commit, with a message that says why. CI (`.github/workflows/ci.yml`) runs on
every push.
