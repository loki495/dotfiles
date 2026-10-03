Audit the public repos and résumé that back my job search, from the perspective of the people
who will actually read them: a recruiter skimming for 30 seconds, a senior engineer opening
the code before an interview, and an outside contributor deciding whether they can help.
Read-only — this command never edits anything, it produces a prioritised report I act on
afterwards.

**Arguments:** $ARGUMENTS

- No argument: audit everything (all repos + the résumé/profile).
- One or more repo names (`insights`, `dibs`, `sessioneer`, `homie`, `dotfiles`): audit only those.
- `resume`: audit only the résumé + profile README.
- `quick`: skip the per-repo deep dives, run only the recruiter/interviewer pass.

---

## Repos in scope

| Repo | Local path | What it is |
| --- | --- | --- |
| `insights` | `~/www/personal/insights` | Laravel + Livewire Volt + Plaid personal-finance app, AGPL-3.0 |
| `dibs` | `~/www/personal/dibs` | Laravel 13 + Livewire 4 + Flux task tracker with a host-local MCP server for coding agents, local SQLite with async GitHub Issues/Projects mirroring, MIT |
| `sessioneer` | `~/www/personal/sessioneer` | PHP + tmux + UNIX-socket UI for managing AI coding agent sessions, MIT |
| `homie` | `~/www/personal/homie` | Laravel 13 + Livewire 4 + Flux home-lab dashboard, MIT |
| `dotfiles` | `~/dotfiles` | Arch/Hyprland desktop + PHP dev tooling, MIT (must live at exactly `~/dotfiles`) |
| profile | `~/dev/loki495-profile` | Profile README + `Andres-Crucitti-PHP-Laravel-Developer.pdf` |

Before launching anything, verify each path exists and is a git repo. If one is missing or
somewhere else, find it (`fd -t d -H '^\.git$' ~ --max-depth 4` or ask me) rather than guessing
or silently skipping it. Report which paths you resolved.

---

## How to run it

Launch **two agents per in-scope repo, plus one recruiter/interviewer agent, all in parallel** and
in the background. Don't audit anything yourself in the main thread — your job is to launch them,
then verify and synthesise what comes back.

Pick each agent's model by the kind of work, not by habit:

- **Scan agent** (repo sections 1 and 6 below: personal/credential data, branches and temp files)
  — mostly mechanical searching and listing with light judgement. Use a mid-tier model (e.g.
  Sonnet).
- **Review agent** (repo sections 2–5, 7 and 8: docs vs. code, fresh-clone walk-through, level
  of detail, interview red flags, contributor readiness, release recommendation) — needs to read
  code and docs together and judge them. Use the strongest model available (e.g. Opus).
- **Recruiter/interviewer agent** — judgement and tone across everything. Strongest model.

Each agent gets: the repo path, its stack (from the table above), which sections it owns, and the
shared rules below.

---

## Rules every agent must follow

**Read-only.** Do not modify, create, or delete any file. Do not run test suites, migrations,
`docker compose up`, `npm install`, or anything that spawns a billable agent process. Reading,
grepping and `git log`/`git show` are fine.

**Verify before reporting.** Every finding must cite `file:line` and quote the offending text.
Confirm a path, class, method, enum case or command actually does or does not exist — never infer
it from a name. A finding you couldn't verify goes in a clearly-marked "unverified" section, not
in the main list.

**Search broadly, not narrowly.** Past audits of these repos missed real leaks because the grep
was scoped too tightly (e.g. searching only for one known domain). When hunting for personal or
client data, search for the *shapes*: any domain-looking string, any absolute path containing a
username, any IP that isn't an RFC5737 documentation address or an obviously-synthetic demo
value, any email address, any `.pem`/key filename. Then judge each hit.

**Check the whole tree, including the boring parts.** Test fixtures, seeders, factories, `.example`
files, committed screenshots (actually render them, don't just list them), docblocks, code
comments, and git history — not just source files. Two of the worst findings in the last audit
were inside a test fixture and a code comment.

**Distinguish tracked from ignored.** Only tracked files matter for anything published. Check
`.gitignore` and `git ls-files` before reporting a local-only file as a leak.

**Judge each file by what it is.** `CLAUDE.md` / `AGENTS.md` / `GEMINI.md` are AI-agent
instruction files — they're allowed to be dense, internal and decision-heavy, so don't flag them
for that. But they *are* public, so personal identifiers and credentials in them still count.
`README.md`, `CONTRIBUTING.md` and `docs/` are user-facing and get judged strictly.

**Don't re-litigate settled decisions.** Check for an existing Dibs plan on this repo
(`todo_list`/`todo_context`, `label=plan`) and this repo's own docs for decisions
already made deliberately. Specifically already decided, do not re-flag:
- `andres@ac495.net` and the `ac495.net` apex domain are **intentionally public** — it's my
  contact address on the résumé. Subdomain *maps* in test fixtures (`homie.ac495.net` etc.) are
  still worth flagging as topology; the apex domain alone is not.
- Committed binaries in `dotfiles/bin/` are a known, deliberate deferral — mention only if
  something has changed.
- **No exact test or assertion counts in public material** (README, docs, profile, résumé, release
  notes). They drift with every commit. Any exact count is itself a finding; suggest either removing
  the number or replacing it with wording that can't go stale. Don't spend effort counting tests to
  check a number — flag the number's presence instead.

**Report what's already good**, briefly, at the end. I need to know what not to touch.

---

## What each repo agent audits, in priority order

1. **Personal, client and credential data.** Absolute paths with a username; LAN/public IPs;
   hostnames, internal domains, SSH aliases/users/ports; client or customer business names; API
   keys, tokens, passwords, private keys (including in `.example` files and fixtures); references
   to private repos or tooling a reader can't access. For each: `file:line`, the quoted text, and
   whether the file is tracked.

2. **Documentation accuracy — does it describe the code as it exists today?** Cover **every**
   tracked documentation file, not just the README: `README.md`, `CONTRIBUTING.md`, `SECURITY.md`,
   `CHANGELOG`/release notes, everything under `docs/`, `.example`/sample config files, inline
   setup comments in compose files and scripts, and the agent instruction files (`CLAUDE.md`,
   `AGENTS.md`, `GEMINI.md`, skill files). List the files you checked. Look for: documented features
   that no longer exist; features that exist but are undocumented; renamed classes/files still
   referred to by old names; commands or paths in docs that don't resolve; setup instructions that
   would fail on a fresh clone; env vars documented but read by no code (and vice versa — grep the
   config class for what's actually read); stated version floors that contradict `composer.json`
   or CI; exact test/assertion counts (see settled decisions); screenshots that no longer match
   the UI.

3. **Can a stranger actually run it?** Walk the documented setup as literally as a first-time
   reader would, from `git clone` to a working app, and identify every step that's missing or
   would fail. Check for: `.env` creation, app-key generation, dependency install, database
   creation, migrations, asset build, and any external network/service the compose file requires.
   State plainly whether a fresh clone works or not.

4. **Appropriate level of detail.** Flag docs that read as private working notes rather than
   documentation: dated changelog entries, "found live on YYYY-MM-DD", notes-to-self, personal
   backlog, the author referred to in the third person, decisions relitigated at length, counters
   that will go stale. Conversely, flag genuinely interesting engineering decisions that are
   buried in an internal file and deserve promoting into user-facing docs — an interviewer should
   be able to find the best story in the repo without reading `CLAUDE.md`.

5. **Anything that would embarrass me in an interview.** Security posture (disabled TLS
   verification, unauthenticated endpoints, permissive CORS/CSRF handling), dead code, personal
   tooling shipped inside a product, committed secrets-adjacent files, licence problems (e.g.
   vendored third-party code under my own licence with no attribution).

6. **Repo hygiene — stale branches and leftover temp files.** Run `git branch -a` and
   `git worktree list` and flag branches that are merged/abandoned and should be deleted (a
   stranger browsing the branch list is part of the impression too). Scan for stray temp/scratch
   artifacts that shouldn't be tracked or lingering: editor swap files, leftover
   scratch/temp scripts, `*.tmp`/`*.bak`, committed local-only output. This audit stays read-only — don't
   delete anything yourself. Just flag what should go; the actual cleanup afterward should go
   through the `git-helper` agent for branch deletion (push-safety checks) and normal file
   deletion for temp files.

7. **Contributor readiness.** Could an outside developer contribute without asking me anything?
   Check that `CONTRIBUTING.md` matches how the project really works (branch to target, the exact
   test/lint commands and whether they run in a container, commit conventions, CI gates a PR must
   pass); that a contributor's local setup is documented separately from an end user's install if
   they differ; that `SECURITY.md` gives a real reporting channel; that the project states its
   maturity (alpha/beta/stable) and known limitations honestly; whether issue/PR templates and
   labels like `good first issue` exist (recommend them only if they'd actually be answered); and
   the state of open Dependabot PRs, failing CI and unanswered issues (use `gh` read-only calls if
   available). Flag anything that only makes sense with access to my machine, my private repos or
   my Dibs instance.

8. **Release recommendation.** End the report with whether this repo warrants a new tag/release
   now — because docs drifted, fixes landed, or features shipped since the last tag (`git describe
   --tags`, `git log <last-tag>..HEAD --oneline`) — and what the release notes should cover. If
   there's no tag yet, say whether the repo is ready for a first prerelease and what blocks it.

---

## What the recruiter/interviewer agent audits

Materials: the résumé PDF (`pdftotext -layout <file> -` to extract), the profile `README.md`, and
all five repos as a reader would encounter them.

1. **Résumé ↔ profile README consistency.** Flag genuine contradictions in stack claims, dates,
   titles, years of experience, project descriptions, CI claims. Any exact test or assertion count
   in either document is a finding in its own right (see settled decisions).

2. **Verify every technical claim against the repos.** Both documents make specific, checkable
   claims — "CI runs the suite against X and Y", "PHPStan/Rector/Pint/Peck gate every
   push", line counts, "no hostname, service, or credential exists anywhere in the code", coverage
   floors. Read the CI YAML and confirm what each job actually runs — a job
   that builds an image is not a job that runs the suite in it. Report anything overstated, stale,
   or unverifiable, and say explicitly what you verified vs. inferred.

3. **The 30-second skim.** What impression does the profile README give? Is the strongest evidence
   surfaced early? What's buried, redundant, or reads as filler/AI boilerplate?

4. **The engineer's read.** Opening these repos before an interview: what impresses, what gives
   pause? Consider README quality, commit message quality, test quality (not just count),
   architecture decisions and whether they're explained, and whether the project looks maintained.

5. **Red flags.** Dead links, broken badges, stale/abandoned appearance, licence problems,
   over-claiming, personal information that shouldn't be public, unprofessional content.

6. **AI-tooling perception.** These repos were built with heavy AI assistance and the history
   shows it (co-author trailers, agent instruction files, session-URL trailers, commits authored
   by a bot rather than by me). Assess honestly how the *artifacts* read to a hiring manager, and
   whether the one-sentence disclosure on the profile is the right dosage, too defensive, or
   contradicted by what the repos actually show.

---

## Output

Each agent returns a prioritised report: highest-impact first, each finding with `file:line`, the
quoted text, why it matters *for the job search specifically*, and a concrete suggested fix with
options where there's a real trade-off. Then a short "already strong, don't touch" list, then (repo
review agents only) the release recommendation.

When they're all back, **verify the top findings yourself** before relaying them — spot-check the
most severe claim from each agent against the actual file. Agents confidently report things that
turn out to be wrong; last time one claimed a test runner swallowed failures and it didn't.

Then give me a single consolidated, deduplicated, cross-repo priority list. Group anything that
appears in more than one repo (the same leak pattern, the same doc-drift class) so I fix it once
everywhere rather than five times. Include a per-repo line on the release recommendation. Tell
me explicitly which items are pure mechanical fixes and which need a decision from me — and
don't start fixing anything until I've picked.
