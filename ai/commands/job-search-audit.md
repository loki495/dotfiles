Audit the public repos and résumé that back my job search, from the perspective of the people
who will actually read them: a recruiter skimming for 30 seconds, and a senior engineer opening
the code before an interview. Read-only — this command never edits anything, it produces a
prioritised report I act on afterwards.

**Arguments:** $ARGUMENTS

- No argument: audit everything (all repos + the résumé/profile).
- One or more repo names (`insights`, `sessioneer`, `homie`, `dotfiles`): audit only those.
- `resume`: audit only the résumé + profile README.
- `quick`: skip the per-repo deep dives, run only the recruiter/interviewer pass.

---

## Repos in scope

| Repo | Local path | What it is |
| --- | --- | --- |
| `insights` | `~/www/insights` | Laravel + Livewire Volt + Plaid personal-finance app, AGPL-3.0 |
| `sessioneer` | `~/www/sessioneer` | PHP + tmux + UNIX-socket UI for managing AI coding agent sessions, MIT |
| `homie` | `~/www/homie` | Laravel 13 + Livewire 4 + Flux home-lab dashboard, MIT |
| `dotfiles` | `~/dotfiles` | Arch/Hyprland desktop + PHP dev tooling, MIT (must live at exactly `~/dotfiles`) |
| profile | `~/dev/loki495-profile` | Profile README + `Andres-Crucitti-PHP-Laravel-Developer.pdf` |

Before launching anything, verify each path exists and is a git repo. If one is missing or
somewhere else, find it (`fd -t d -H '^\.git$' ~ --max-depth 4` or ask me) rather than guessing
or silently skipping it. Report which paths you resolved.

---

## How to run it

Launch **one agent per in-scope repo, plus one recruiter/interviewer agent, all in parallel** and
in the background. Don't audit anything yourself in the main thread — your job is to launch them,
then verify and synthesise what comes back.

Each agent gets: the repo path, its stack (from the table above), and the shared rules below.

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

**Don't re-litigate settled decisions.** Check `.ai/plans/` and this repo's own docs for
decisions already made deliberately. Specifically already decided, do not re-flag:
- `andres@ac495.net` and the `ac495.net` apex domain are **intentionally public** — it's my
  contact address on the résumé. Subdomain *maps* in test fixtures (`homie.ac495.net` etc.) are
  still worth flagging as topology; the apex domain alone is not.
- Committed binaries in `dotfiles/bin/` are a known, deliberate deferral — mention only if
  something has changed.

**Report what's already good**, briefly, at the end. I need to know what not to touch.

---

## What each repo agent audits, in priority order

1. **Personal, client and credential data.** Absolute paths with a username; LAN/public IPs;
   hostnames, internal domains, SSH aliases/users/ports; client or customer business names; API
   keys, tokens, passwords, private keys (including in `.example` files and fixtures); references
   to private repos or tooling a reader can't access. For each: `file:line`, the quoted text, and
   whether the file is tracked.

2. **Documentation accuracy — does it describe the code as it exists today?** Documented features
   that no longer exist; features that exist but are undocumented; renamed classes/files still
   referred to by old names; commands or paths in docs that don't resolve; setup instructions that
   would fail on a fresh clone; env vars documented but read by no code (and vice versa — grep the
   config class for what's actually read); stated version floors that contradict `composer.json`
   or CI; test counts that don't match a real count.

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

---

## What the recruiter/interviewer agent audits

Materials: the résumé PDF (`pdftotext -layout <file> -` to extract), the profile `README.md`, and
all four repos as a reader would encounter them.

1. **Résumé ↔ profile README consistency.** Flag genuine contradictions in test counts, stack
   claims, dates, titles, years of experience, project descriptions, CI claims. Note that the
   README deliberately carries exact numbers while the résumé rounds ("600+ tests") — that's
   intentional, not an inconsistency.

2. **Verify every technical claim against the repos.** Both documents make specific, checkable
   claims — test counts, "CI runs the suite against X and Y", "PHPStan/Rector/Pint/Peck gate every
   push", line counts, "no hostname, service, or credential exists anywhere in the code", coverage
   floors. Count things for real. Read the CI YAML and confirm what each job actually runs — a job
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
options where there's a real trade-off. Then a short "already strong, don't touch" list.

When they're all back, **verify the top findings yourself** before relaying them — spot-check the
most severe claim from each agent against the actual file. Agents confidently report things that
turn out to be wrong; last time one claimed a test runner swallowed failures and it didn't.

Then give me a single consolidated, deduplicated, cross-repo priority list. Group anything that
appears in more than one repo (the same leak pattern, the same doc-drift class) so I fix it once
everywhere rather than four times. Tell me explicitly which items are pure mechanical fixes and
which need a decision from me — and don't start fixing anything until I've picked.
