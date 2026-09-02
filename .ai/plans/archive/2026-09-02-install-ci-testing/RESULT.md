# Results

## T2: assert-symlinks.sh (done)

Built `scripts/ci/assert-symlinks.sh`. Re-verified all 6 install sections directly
(not from the prompt summary) - the exact expected symlink/file pairs are listed in
the script's own PASS/FAIL labels, one section at a time matching
10-bash/20-git/30-desktop-config/40-systemd/50-ai-tools/60-neovim.

**Important finding for T5/T6 (driver script / CI workflow)**: `bash/bashrc`'s very
first line is `. ~/dotfiles/bash/lib/colors` (unconditional, no existence guard),
and it also hardcodes `~/dotfiles/bash/.bash_aliases`, `~/dotfiles/backup-tools`,
`~/dotfiles/bin`, and `~/dotfiles/git/.git-completion.bash` later on - all assuming
the repo lives at literally `$HOME/dotfiles`, independent of where `install.sh`
itself was actually invoked from (which correctly uses `$SCRIPTPATH` via
`BASH_SOURCE`). **T5's container setup must symlink or clone the checked-out repo
to `$HOME/dotfiles`** before running `install.sh`, or the `~/.bashrc` sourcing
check (and real `.bashrc` usage) will fail in CI. This is a pre-existing property
of `bash/bashrc`, not something I changed - flagging rather than fixing since it's
out of T2's scope.

**Testing approach**: could not run `install.sh` itself to generate the "correct"
fixture (that's T5's job, and PLAN.md's safety constraint says never run it against
a real $HOME) - so I manually constructed fake `$HOME`s with symlinks matching
what each section's own script says it creates, verified by reading those scripts
directly.

Three cases verified against a fresh `$HOME=$(mktemp -d)` each time (never the real
$HOME), plus a repo symlink at `$HOME/dotfiles` for the bashrc check:
1. **Full setup** (matches this dev machine, which has opencode/codex/agy
   installed): all 46 checks PASS, exit 0.
2. **Minimal CI-like setup** (opencode/codex/agy absent - built a scratch `PATH`
   containing only symlinks to core tools actually needed, no AI CLIs): the three
   conditional blocks correctly print `SKIP: ... not installed in this
   environment` instead of failing, 21 checks PASS, exit 0. This matches what the
   real CI container will look like (T6) unless those tools are deliberately
   installed there.
3. **Deliberately broken symlink** (pointed `~/.bashrc` at `bash/dircolors`
   instead of `bash/bashrc`): correctly reported
   `FAIL: ~/.bashrc -> bash/bashrc - ... resolves to .../bash/dircolors, expected
   .../bash/bashrc` and exited 1.

No blockers, no QUESTIONS.md entry needed. Script is read-only/assertion-only, made
no changes to any real system state; all three test fixtures were built in and torn
down from `mktemp -d` throwaway directories.

## T4: tmux-based nvim highlighting check (done)

Built `scripts/ci/test-nvim-highlighting.sh` plus one fixture file per language
under `scripts/ci/fixtures/` (separate files, not inline heredocs - easier to
inspect/edit independently and avoids quoting collisions with tmux send-keys'
own quoting). Filetype list and the `sh->bash`/`typescriptreact->tsx` exceptions
were re-read directly from `nvim/lua/andres/autocmds.lua`, not assumed from the
prompt: 11 filetypes total (sh, html, yaml, javascript, typescript,
typescriptreact, vue, json, php, rust, toml).

**Design decision - prerequisite handling**: the script does NOT call
`install_neovim.sh --parsers/--queries` itself. It assumes parsers/queries are
already installed (they were, on this dev machine, from earlier this session) and
assumes `~/.config/nvim` already resolves to this repo (true on this machine, and
guaranteed in the real pipeline once `install.sh`'s `60-neovim.sh` section has run
- since a plain `nvim <file>` needs the repo's `nvim/lua/andres/*` modules on
`runtimepath`, which only happens via that symlink, NOT via `nvim -u <repo>/nvim/
init.lua` - `-u` only overrides which init file loads, not runtimepath). **T5 must
run `install_neovim.sh --parsers`/`--queries` and ensure the `~/.config/nvim`
symlink exists BEFORE calling this script.**

**Error-marker heuristic**: settled on `"Press ENTER or type command to
continue"`, `"E117:"`, `"E5108:"`, `"Error in "`, `"Error executing"` -
deliberately NOT bare `"Error"` or bare `"traceback"`. Verified empirically: the
benign, once-per-process nvim-lspconfig deprecation notice (tailwind-tools
triggers `vim.deprecate(..., backtrace=true)`) legitimately prints its own
"stack traceback:" section as part of the *expected*, non-blocking notice - a
bare "traceback" marker would have been a false positive on every single run.
Captured a live occurrence of this notice and grepped it against the chosen
marker list to confirm zero matches.

**Detection design - two independent signals, not just color counting.** The
original design (per PLAN.md) was color-count only: >=3 distinct `38;2;r;g;b`
truecolor codes across a `capture-pane -e` dump. Testing this against a
deliberately-broken parser (see below) revealed color-counting ALONE is
insufficient: Neovim's legacy regex `:syntax` highlighting also produces several
distinct colors independent of treesitter, so a broken/missing treesitter parser
still passed the color check. Added a ground-truth signal first: after cursor
movement, send `:lua print('TSACTIVE=' .. tostring(vim.treesitter.highlighter
.active[vim.api.nvim_get_current_buf()] ~= nil))` into the nvim instance via
tmux, capture, and require `TSACTIVE=true`. Color counting is kept as a second,
independent check (catches "attached but somehow not rendering"). See the new
shared lesson `.ai/lessons/neovim-treesitter-parser-lookup.md` for the two
underlying gotchas this surfaced (parser lookup globs the filename so renaming
in place doesn't hide it; `get_parser`/`start` fail via return value, not throw
- both cost real debugging time before landing on `highlighter.active` as the
reliable check).

**Verification**:
1. Full run against this machine's real, already-fixed nvim config: 11/11 PASS,
   exit 0 (`html: 5, javascript: 3, json: 7, php: 3, rust: 14, sh: 10, toml: 6,
   typescript: 5, typescriptreact: 9, vue: 5, yaml: 5` distinct colors - all
   above the 3-color floor).
2. Deliberate-failure case: moved `rust.so` fully out of `~/.local/share/nvim/
   site/parser/` (to `/tmp`, not renamed in-place - see lesson above),
   re-ran for just `rust`: correctly reported `FAIL rust: vim.treesitter
   .highlighter is NOT active for this buffer (lang=rust)` with a hint pointing
   at the missing parser path, exit 1. Restored the file immediately after;
   confirmed present again and the full suite back to 11/11 PASS.
3. Confirmed the benign deprecation notice actually fires during these runs
   (captured raw pane text containing "deprecated"/"stack traceback") and that
   none of the five chosen error markers match it.

No blockers, no QUESTIONS.md entry needed. Environment left exactly as found
(parser restored, no stray tmux sessions - `tmux kill-session` called on every
exit path including failures). Did not touch `nvim/lua/andres/autocmds.lua` or
`scripts/ci/assert-symlinks.sh` (T2, owned by the concurrent worker).

**Remaining concern for T5's author**: the script currently takes ~15-20s total
for all 11 languages (tmux launch + sleep + capture per language, sequentially).
Fine for a CI job but worth knowing if T5 wants to budget/parallelize.

## T7: local Docker dry-run (done)

Two fork attempts each hit a session-wide Claude rate limit mid-task (unrelated
to task correctness - infrastructure, not a bug). Orchestrator completed the
final verification directly once Bash access was restored (a separate, also-
unrelated /tmp-full incident blocked Bash entirely for a while - see STATE.md,
fully resolved, root cause was a stray 5.7G orphaned opencode source checkout,
nothing to do with this plan).

Two real bugs found and fixed:

1. **git https->ssh rewrite breaks clones in a container.** `git/.gitconfig`
   (symlinked to ~/.gitconfig by 20-git.sh) has
   `[url "git@github.com:"] insteadOf = https://github.com/`, rewriting every
   plain https clone to SSH. Works fine on a real dev machine with SSH keys
   set up; breaks every clone `install_neovim.sh --parsers/--queries` does
   inside a throwaway container with no SSH agent. Fixed in
   scripts/ci/test-install.sh: `export GIT_CONFIG_GLOBAL=/dev/null` right
   after the install.sh step - confirmed this bypasses the rewrite without
   mutating the actual tracked git/.gitconfig file (unlike
   `git config --global --unset`, which would edit it through the symlink).

2. **Fresh $HOME never bootstraps lazy.nvim's plugins.** See the new lesson
   `.ai/lessons/lazy-nvim-fresh-home-needs-sync.md` (also copied to the
   machine-wide `ai/lessons/`) for the full mechanism. Fixed by adding
   `timeout 180 nvim --headless "+Lazy! sync" +qa` as step 5/6 in
   test-install.sh, before the highlighting check (step 6/6).

**Final verified run**: orchestrator ran the real, complete, unmodified
scripts/ci/test-install.sh via `docker exec` into an archlinux:latest
container (already had both fixes' prerequisites - deps installed, lazy.nvim
plugins built - from the interrupted second attempt, reused rather than
discarded to avoid redoing the slow parts). All 6 steps passed: install.sh,
assert-symlinks.sh (22/22), install_neovim.sh --parsers, install_neovim.sh
--queries, Lazy! sync, test-nvim-highlighting.sh (11/11 languages). Zero
FAILED/FATAL markers anywhere in the full log. `=== ALL CHECKS PASSED ===`.
Container removed after (`docker rm -f`) per the orchestrator-worker skill's
Background Launch Verification update.

No blockers, no open QUESTIONS.md entry. Did not touch
nvim/lua/andres/autocmds.lua's filetype/language behavior.
