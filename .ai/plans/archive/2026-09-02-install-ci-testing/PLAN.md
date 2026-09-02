# Plan: test the whole dotfiles install + GitHub Actions CI

## Objective

Automated testing for `install.sh` (all `scripts/install/*.sh` sections, not just
neovim) plus `install_neovim.sh`, wired into a GitHub Actions workflow. Includes a
tmux-based check that nvim actually renders real (non-default) syntax highlighting
with no error popups, reusing the manual debugging technique from the
2026-09-01/02 nvim-fix session (see RESULT.md of that session's conversation - not
a plan file, this is the first plan in this repo).

## CRITICAL SAFETY CONSTRAINT

`install.sh` (and its sections) symlink real dotfiles onto `$HOME`
(`~/.bashrc`, `~/.gitconfig`, `~/.config/systemd`, `~/.config/nvim`, `~/.claude/*`,
etc.) and run `systemctl --user daemon-reload`. **Never run `install.sh` for real
against this machine's actual `$HOME`** - it would clobber Andres's live config.
All test/dry-runs (local iteration in task T7, and CI itself) MUST run inside an
isolated container (`docker run` locally, the GitHub Actions container in CI) with
its own throwaway `$HOME`. Any worker on this plan must re-read this constraint
before touching anything that invokes `install.sh` or its sections directly.

## Background / already known

- `install.sh` sources `scripts/install/{10-bash,20-git,30-desktop-config,
  40-systemd,50-ai-tools,60-neovim}.sh` in order (or a filtered subset by name).
- `40-systemd.sh` runs `systemctl --user daemon-reload` - needs a real user
  systemd session, not present in a plain container. Plan: stub `systemctl` as a
  no-op earlier in `PATH` inside the test container, so the symlinking still gets
  exercised without needing systemd-in-Docker.
- `60-neovim.sh` is interactive (`read -rp` for user-local vs global choice) -
  needs a non-interactive override for CI (see T1).
- `50-ai-tools.sh`'s opencode/codex/agy sections are already guarded with
  `command_exists` checks and just print "not found, skipping" when absent - safe
  as-is in a minimal CI container missing those tools.
- `install_neovim.sh` already has `--parsers [lang...]` and `--queries [lang...]`
  modes (added earlier this session) - both default to the full language list
  (`bash html yaml javascript typescript tsx vue json php rust toml`) if none
  given, and both accept an explicit subset.
- nvim's `lua/andres/autocmds.lua` wires `vim.treesitter.start()` per filetype -
  see that file for the exact filetype list and filetype->language exceptions
  (`sh`->`bash`, `typescriptreact`->`tsx`).
- CI container choice: Arch Linux (`archlinux:latest` or similar), since
  `install_neovim.sh --parsers` hardcodes `sudo pacman -S --needed tree-sitter-cli`
  - not worth making the script distro-agnostic for this.
- Tools confirmed installed on this machine as of 2026-09-02: opencode, codex, agy,
  docker (no podman).

## Tasks

### T1: non-interactive override for 60-neovim.sh
- Status: done
- Objective: let CI (and any non-interactive rerun) skip the `read -rp` prompt.
- Files: `scripts/install/60-neovim.sh`
- Approach: honor an env var (e.g. `NVIM_INSTALL_CHOICE=1|2`) before falling back
  to the interactive prompt. Keep default interactive behavior unchanged when the
  var is unset.
- Acceptance: `NVIM_INSTALL_CHOICE=1 bash scripts/install/60-neovim.sh` runs
  install_neovim.sh --user without prompting; running with the var unset still
  prompts as before.
- Owner: orchestrator (small, not worth delegating).

### T2: assert-symlinks.sh
- Status: done
- Objective: after `install.sh` runs (in an isolated container/HOME - see safety
  constraint), assert every symlink each section is supposed to create actually
  exists and points at the right repo path, and that `~/.bashrc` sources cleanly
  (`bash -c "source ~/.bashrc"` exits 0).
- Files (new): `scripts/ci/assert-symlinks.sh`
- Depends on: reading all of `scripts/install/*.sh` for the exact expected
  target->source pairs (already read this session, see PLAN background above -
  don't re-derive, the worker should still verify against the actual files itself
  per the worker protocol).
- Acceptance: script exits 0 when all expected symlinks/configs are correct, exits
  non-zero with a clear per-check message on any mismatch.
- Owner: candidate for a fork (inherits the section-by-section detail already
  gathered this session) or a cheap fresh worker if fork context isn't needed by
  then - decide at launch time.

### T3: systemctl stub for the test container
- Status: done
- Objective: a no-op `systemctl` shim so `40-systemd.sh`'s
  `systemctl --user daemon-reload` doesn't fail without a real user systemd
  session, while still letting that section's symlinking run for real.
- Files (new): `scripts/ci/stubs/systemctl` (executable shim), referenced by
  prepending its directory to `PATH` in both the CI workflow and any local
  Docker-based dry run.
- Acceptance: `40-systemd.sh` completes successfully in a container with this
  stub on `PATH` and no real systemd user session.
- Owner: orchestrator (small, bundle with T1/T2 review rather than a separate
  worker launch).

### T4: tmux-based nvim highlighting check
- Status: done
- Objective: automate the manual technique used throughout the 2026-09-01/02
  debugging session - for each language nvim-treesitter used to cover
  (reuse the `TS_QUERY_LANGS` list from `install_neovim.sh` - bash/sh, html,
  yaml, javascript, typescript, tsx, vue, json, php, rust, toml), open a small
  real test snippet in a detached tmux session running nvim, move the cursor a
  few times (not just open-and-capture - that's what actually caught the
  treesitter-context crash originally), then `tmux capture-pane -p -e` and
  assert:
    1. more than one distinct truecolor foreground escape code appears across
       the buffer's content lines (proof real highlighting happened, not a
       flat/default color for everything);
    2. none of the known error-popup markers appear (e.g. "Error", "traceback",
       "Press ENTER or type command to continue", "E117") - the deprecation
       notice from nvim-lspconfig is expected/benign and should NOT fail the
       check, see RESULT.md once confirmed which exact strings distinguish it.
- Files (new): `scripts/ci/test-nvim-highlighting.sh`, small fixture snippets per
  language (inline heredocs in the script, or `scripts/ci/fixtures/<lang>.<ext>` -
  worker's call, record the choice in RESULT.md).
- This is the highest tool-call/iteration task on this plan (lots of tmux
  capture/inspect cycles, likely several attempts to get the "distinct colors"
  and "no errors" heuristics right) - a strong candidate for delegation per the
  orchestrator-worker skill's cost argument, independent of model price.
- Acceptance: script exits 0 against the current, already-fixed nvim config for
  all languages in the list; demonstrably would have failed against the
  pre-fix state for at least the markdown-crash and "plain/no highlighting"
  cases (verify by temporarily reproducing, don't just assert this in prose).
- Owner: fork (inherits this session's tmux-capture-pane methodology directly,
  avoids re-deriving it) - orchestrator to confirm at launch time this is still
  the right call vs. a fresh cross-tool worker.

### T5: driver script tying it together
- Status: done
- Objective: `scripts/ci/test-install.sh` - runs `install.sh` (with the T1
  env-var override) inside whatever isolated HOME/container it's called from,
  runs T2's assert-symlinks.sh, runs `install_neovim.sh --parsers` and
  `--queries` (full language set - see below for why not the fast subset
  originally sketched), then runs T4's test-nvim-highlighting.sh (also full
  set, no args). Non-zero exit and clear diagnostic on first failure.
- **Design change from original sketch**: originally planned to only install
  a fast parser subset (`json bash`) in CI for speed. Dropped once T4's script
  existed and iterates all 11 languages by default - installing only 2 parsers
  would make 9/11 of T4's checks fail for a reason unrelated to any real bug
  (parser deliberately not installed, not "broken install"). Testing the full
  matrix is the actual point of building T4 at all; accepted the extra
  TypeScript/Vue npm-install time as the cost of real coverage. Can revisit if
  CI proves too slow/flaky in practice.
- Explicit safety gate: refuses to run at all unless `DOTFILES_CI_TEST=1` is
  set by the caller, and refuses unless the repo is checked out at exactly
  `$HOME/dotfiles` (per T2's bashrc finding) - both verified working.
- Integration bug caught while writing this (not by a worker - reasoned
  through directly): `install_neovim.sh --user` puts `nvim` at
  `$HOME/.local/bin/nvim` but never modifies `PATH` itself, so
  test-nvim-highlighting.sh's `nvim` invocation would fail with "not found" in
  a fresh container unless this script exports that PATH addition itself,
  which it now does right after the install.sh step.
- Owner: orchestrator (integration work, needs judgment about ordering/failure
  reporting across all the other tasks' outputs).

### T6: GitHub Actions workflow
- Status: done
- Wrote `.github/workflows/ci.yml`: `archlinux:latest` container job, `HOME`
  forced to `/root` explicitly (rather than trusting whatever GH Actions'
  container-job HOME convention actually is - this is the one part of this
  task that can only be fully confirmed by a real run, see T8), installs
  git/curl/wget/tar/tmux/base-devel/nodejs/npm/tree-sitter-cli up front so
  install_neovim.sh's own conditional pacman-install of tree-sitter-cli never
  triggers (avoids its lack of `--noconfirm` hanging CI), symlinks the
  checkout to `$HOME/dotfiles`, prepends `scripts/ci/stubs/` to PATH, runs
  `test-install.sh` with `DOTFILES_CI_TEST=1`. Triggers: push touching
  install.sh/scripts/install/scripts/ci/nvim/the workflow file itself, plus
  workflow_dispatch. YAML syntax validated (python yaml.safe_load), not yet
  run for real (T7/T8).
- Also added `scripts/ci/stubs/sudo` (exec passthrough - container already
  runs as root) alongside T3's systemctl stub, since install_neovim.sh's
  parser-install fallback and 60-neovim.sh's --global path both call sudo,
  even though neither is actually reached by the CI path chosen here.
- Objective: `.github/workflows/ci.yml` - Arch Linux container
  (`archlinux:latest` or similar), installs base deps (git, curl, wget, tar,
  tmux, sudo, base-devel, nodejs, npm, tree-sitter-cli), checks out the repo,
  runs `scripts/ci/test-install.sh`. Triggers: push touching
  `install.sh`/`scripts/install/**`/`install_neovim.sh`/`nvim/**`, plus
  `workflow_dispatch` for manual runs.
- Depends on: T5 done.
- Owner: orchestrator or cheap fresh worker (mechanical once T5 exists).

### T7: local dry-run before pushing
- Status: done
- Objective: run `scripts/ci/test-install.sh` inside a real local
  `docker run` (Arch image, throwaway container - NEVER the host $HOME, see
  safety constraint) to catch container/environment issues before spending CI
  minutes and push cycles on them.
- Took two fork attempts (both hit session-wide rate limits mid-task, unrelated
  to this task's correctness - see STATE.md) plus final verification done
  directly by the orchestrator once Bash access was restored. Two real bugs
  found and fixed across the attempts:
  1. `git/.gitconfig`'s `insteadOf` rewrite (https -> ssh) breaks every clone
     `install_neovim.sh --parsers/--queries` does inside a container with no
     SSH agent - fixed via `GIT_CONFIG_GLOBAL=/dev/null` in test-install.sh.
  2. A fresh `$HOME` has never launched nvim before, so lazy.nvim's plugins
     are never installed/compiled - without an explicit `Lazy! sync` step,
     6/11 languages in the highlighting check failed, not from missing
     parsers but from a hard Lua error in an uncompiled native plugin
     (telescope-fzf-native) interrupting nvim's startup before some
     autocmds.lua FileType autocmds registered. Fixed by adding
     `timeout 180 nvim --headless "+Lazy! sync" +qa` as step 5/6 in
     test-install.sh, before the highlighting check.
- **Final verified run** (orchestrator, direct docker exec into a container
  that already had both fixes' prerequisites from the interrupted attempt):
  all 6 steps passed cleanly, `assert-symlinks.sh` 22/22,
  `test-nvim-highlighting.sh` 11/11, `=== ALL CHECKS PASSED ===`. Zero FAILED/
  FATAL markers anywhere in the full log. Container removed after.
- Owner: fork or general-purpose worker with a strong-enough model - likely
  needs several run/inspect/fix iterations (container quirks, missing deps),
  which is exactly the "contains iteration cost inside a disposable worker"
  case from the orchestrator-worker skill's Model Tiering section.

### T8: push + verify real CI run
- Status: done
- Objective: commit the new scripts/workflow, push, watch the actual GitHub
  Actions run, iterate on any CI-only failures (network/container differences
  from local docker) until green.
- Committed as f21ee5d, pushed to origin/master (confirmed with Andres first,
  per the hard rule on stating branch+remote before any push). Watched the
  real run (33685091371) via `gh run watch --exit-status`: all 9 steps green
  in 2m27s, exit 0, confirmed by re-checking the actual CI log for the
  highlighting check's real PASS lines (not just trusting the green checkmark).
  One unrelated GitHub-platform annotation (actions/checkout's Node 20
  deprecation notice) - not something in this repo's control, not a failure.
  No CI-only issues surfaced beyond what T7's local Docker run already found
  and fixed - first real push was green.
- Depends on: T7 passing locally first.
- Owner: orchestrator (needs `gh` CLI / push access and back-and-forth judgment
  calls on failures - not a good fit for a disposable worker that can't push).

## Acceptance criteria (whole plan)

1. `install.sh` (all sections) and `install_neovim.sh --parsers/--queries` are
   exercised for real inside an isolated container, not just syntax-checked.
2. The tmux-based nvim check proves actual per-token syntax highlighting for
   every currently-supported language, and proves no error popups appear either
   on open or after some cursor movement.
3. A GitHub Actions workflow runs all of the above on relevant pushes and on
   `workflow_dispatch`, and a real run is green.
4. No changes were made to Andres's actual `$HOME`/live config in the process of
   building or testing any of this.
