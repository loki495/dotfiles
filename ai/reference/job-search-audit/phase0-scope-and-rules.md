# Phase 0 (scope, freshness gate) and rules every agent must follow

Reference for the `job-search-audit` command; read it at the step the command names.

## Phase 0: scope and staleness gate

**Scope.** The repos are the Dibs atlas parents (`todo_list` label `feature atlas`, one per repo,
titled `Feature atlas: <Project>`). Each parent's `Repo:` line gives the local path and remote, and
its Purpose and Stack lines say what the repo is; do not keep a copy of that here. Verify each path
exists and is a git repo; if one is missing or elsewhere, find it or ask me, never guess or skip
silently. Report the paths you resolved. A repo without an atlas parent is reported as out of scope
and `/feature-atlas` is recommended; do not audit it from guesses.

The profile materials are the exception, because they have no atlas: `~/dev/loki495-profile`
(profile `README.md` + `Andres-Crucitti-PHP-Laravel-Developer.pdf`) and `~/www/LinkedIn-Profile.pdf`,
a print of my own logged-in LinkedIn page. Ignore its private and navigation noise ("Private to
you", analytics, "People you may know", suggestions); judge only what a visitor sees (headline,
About, Featured, Experience, Education, Skills). If its file date is older than the résumé's,
say so and ask me for a fresh export before grading it.

**Freshness gate, before anything else.** Per repo: the working tree must be clean (`git status
--porcelain` empty on the default branch) and local must equal the fetched origin tip. If either
fails, say the atlas can't be confirmed against that code and stop, or read from a detached
worktree at the origin tip. Then compare each subsystem comment's `verified-at` with the tip
(`git diff --name-only <sha>..<tip> -- <owned paths>`). A subsystem whose files changed, or whose
comment is partial, has unverified facts: name it in the output. Never rewrite the atlas from the
audit; recommend a refresh. Git is the drift record; keep no separate checksums.

**Prior state.** Look for an open `Job search audit: <date>` task and the repo's open `bug`,
`docs drift` and `portfolio` tasks (`todo_list`), so known items are not re-filed (see phase 4).
The previous run's file-accounting list rotates the phase 3 sample.

## Rules every agent must follow

**No repo edits.** Do not modify, create, or delete any file in an audited repo or the résumé
materials. Do not run `docker compose up`, `npm install`, migrations, or anything that spawns a
billable agent process. Reading, grepping, `git log`/`git show`, `gh` read calls and the scans in
phase 2 are fine. Running a project's own test suite is not read-only (it writes caches, may use a
database, may start containers): it happens only in phase 4 under the rules there. Findings are
written to Dibs by the orchestrator only; workers return them.

**Verify before reporting.** Every finding must cite `file:line` and quote the offending text.
Confirm a path, class, method, enum case or command actually does or does not exist; never infer
it from a name. A finding you couldn't verify goes in a clearly-marked "unverified" section, not
in the main list.

**Search broadly, not narrowly.** Past audits of these repos missed real leaks because the grep
was scoped too tightly (e.g. searching only for one known domain). When hunting for personal or
client data, search for the *shapes*: any domain-looking string, any absolute path containing a
username, any IP that isn't an RFC5737 documentation address or an obviously-synthetic demo
value, any email address, any `.pem`/key filename. Then judge each hit.

**Check the whole tree, including the boring parts.** Test fixtures, seeders, factories, `.example`
files, committed screenshots (actually render them, don't just list them), docblocks, code
comments, and git history, not just source files. Two of the worst findings in an earlier audit
were inside a test fixture and a code comment.

**Distinguish tracked from ignored.** Only tracked files matter for anything published. Check
`.gitignore` and `git ls-files` before reporting a local-only file as a leak.

**Judge each file by what it is.** `CLAUDE.md` / `AGENTS.md` / `GEMINI.md` are AI-agent
instruction files: they're allowed to be dense, internal and decision-heavy, so don't flag them
for that. But they *are* public, so personal identifiers and credentials in them still count.
`README.md`, `CONTRIBUTING.md` and `docs/` are user-facing and get judged strictly.

**Don't re-litigate settled decisions.** Check for an existing Dibs plan on this repo
(`todo_list`/`todo_context`, `label=plan`) and this repo's own docs for decisions already made
deliberately. Specifically already decided, do not re-flag:
- `andres@ac495.net` and the `ac495.net` apex domain are **intentionally public**: it's my
  contact address on the résumé. Subdomain *maps* in test fixtures (`homie.ac495.net` etc.) are
  still worth flagging as topology; the apex domain alone is not.
- Committed binaries in `dotfiles/bin/` are a known, deliberate deferral; mention only if
  something has changed.
- **No exact test or assertion counts in public material** (README, docs, profile, résumé, release
  notes). They drift with every commit. Any exact count is itself a finding; suggest either removing
  the number or replacing it with wording that can't go stale. Don't spend effort counting tests to
  check a number: flag the number's presence instead.

**Report what's already good**, briefly, at the end. I need to know what not to touch.
