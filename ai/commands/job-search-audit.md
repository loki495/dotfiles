Audit the public repos and résumé that back my job search, from the perspective of the people
who will actually read them: a recruiter skimming for 30 seconds, a senior engineer opening
the code before an interview, and an outside contributor deciding whether they can help.
It edits no repo, résumé or profile file: it files findings in Dibs and produces a prioritised
report I act on afterwards. The one write it makes is the proposed wording in the two notes files
(see "Notes files").

**Arguments:** $ARGUMENTS

- No argument: audit everything (the five repos + the résumé, profile README and LinkedIn).
- One or more repo names (`insights`, `dibs`, `sessioneer`, `homie`, `dotfiles`): audit only those.
- `resume`: audit only the résumé, profile README and LinkedIn.
- `quick`: skip the per-repo reader-lens deep dives (phase 3), run only phases 0-2 and the
  recruiter/interviewer pass.
- `tools`: also run each project's own test and lint commands (phase 4, see its rules).

The audit has phases, run in order per repo. Repos run in parallel; phases within a repo do not.

| Phase | What | Model |
| --- | --- | --- |
| 0 | Scope and staleness gate | orchestrator |
| 1 | Facts from the atlas | Sonnet |
| 2 | Tool checks (breadth) | Sonnet |
| 3 | Reader-lens checks (independent of the atlas) | Sonnet gathers, Opus judges |
| 4 | Findings and report | Opus |

---

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

---

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

---

## Phase 1: facts from the atlas

Read the repo's atlas parent and the subsystem comments (stack, entrypoints, interfaces, tests,
dependencies, known mismatches). Use them as a map of the repo, not as proof; the atlas tells you
what to compare, phase 3 does the comparing.

**Docs against the atlas.** Compare each claim in the README, CONTRIBUTING, SECURITY, `docs/`,
`CLAUDE.md`/`AGENTS.md` and `.example` files with the subsystem it describes. A claim that matches
nothing in the atlas, or contradicts it, is a lead, not yet a finding: confirm it in the code
before it becomes a `docs drift` finding. The atlas's own recorded mismatches are leads too.

**Known limitations.** A repo's public docs must match its open `bug` tasks: a known bug the docs
don't mention, or a documented limitation with no open bug and no fix, is a `docs drift` finding.

Output: the lead list and the list of unverified subsystems from phase 0. No findings yet.

---

## Phase 2: tool checks (breadth)

Mechanical scans over the whole tree, one worker per repo. Everything here is read-only:

- Secret and personal-data scan across the **full git history**, not just the tip (`gitleaks` or
  `trufflehog` if installed, otherwise the shape greps from the rules above over `git log -p`).
  For each hit: tracked or not, and whether it is still in the tip.
- README and docs link check (relative paths resolve, external URLs answer, badges render).
- CI status: latest default-branch run per workflow, open Dependabot PRs, failing checks (`gh`
  read calls). Read the workflow YAML and note what each job actually runs; a job that builds an
  image is not a job that runs the suite in it. CI results are the default evidence that the
  project's tests pass.
- Static greps: documented env vars against what the config class reads (and the reverse), stated
  version floors against `composer.json`/CI, exact test counts in public docs.
- Hygiene: `git branch -a`, `git worktree list`, stale merged/abandoned branches, stray temp or
  scratch files (swap files, `*.tmp`/`*.bak`, committed local output). Don't delete anything; flag
  what should go (branch deletion afterwards goes through the `git-helper` agent).

Workers return compact evidence (about 300 words), not raw output.

---

## Phase 3: reader-lens checks (independent of the atlas)

These checks judge what a reader sees, so they must not borrow their conclusions from the atlas.
The worker reads the files itself.

**Sample.** About 10 to 15 tracked files per repo, chosen fresh each run: always the entrypoint,
the largest or most complex file, and the most recently changed files; then one randomly chosen
file per subsystem, with extra weight on files in a partial comment's not-read globs. Prefer files
the previous run didn't sample.

**Tripwire.** Compare every sampled file with its subsystem comment. A mismatch is an atlas drift
finding and marks that subsystem unverified until it's refreshed. If more than a couple of sampled
files disagree, say plainly that the atlas can't be trusted for that repo yet and recommend a
refresh before relying on phases 1 and 2.

Lenses, in priority order:

1. **Personal, client and credential data** (confirm phase 2 hits in the sample; read fixtures,
   docblocks and comments by eye). Absolute paths with a username; LAN/public IPs; hostnames,
   internal domains, SSH aliases/users/ports; client or customer business names; API keys,
   tokens, passwords, private keys (including in `.example` files and fixtures); references to
   private repos or tooling a reader can't access.

2. **Can a stranger actually run it?** Walk the documented setup as literally as a first-time
   reader would, from `git clone` to a working app, by reading it, and identify every step that's
   missing or would fail: `.env` creation, app-key generation, dependency install, database
   creation, migrations, asset build, and any external network/service the compose file requires.
   State plainly whether a fresh clone works or not. If the docs claim a demo, check it exists and
   that its path to a first working screen is documented.

3. **Documentation accuracy, every tracked doc.** Not just the README: `CONTRIBUTING.md`,
   `SECURITY.md`, `CHANGELOG`/release notes, `docs/`, `.example` files, inline setup comments in
   compose files and scripts, and the agent instruction files. List the files checked. Look for:
   documented features that no longer exist; features that exist but are undocumented; renamed
   classes/files still referred to by old names; commands or paths that don't resolve; setup
   instructions that would fail on a fresh clone; screenshots that no longer match the UI.

4. **Appropriate level of detail.** Flag docs that read as private working notes rather than
   documentation: dated changelog entries, "found live on YYYY-MM-DD", notes-to-self, personal
   backlog, the author referred to in the third person, decisions relitigated at length, counters
   that will go stale. Conversely, flag genuinely interesting engineering decisions buried in an
   internal file that deserve promoting into user-facing docs: an interviewer should be able to
   find the best story in the repo without reading `CLAUDE.md`.

5. **Anything that would embarrass me in an interview.** Security posture (disabled TLS
   verification, unauthenticated endpoints, permissive CORS/CSRF handling), dead code, personal
   tooling shipped inside a product, committed secrets-adjacent files, licence problems (e.g.
   vendored third-party code under my own licence with no attribution).

6. **Contributor readiness.** Could an outside developer contribute without asking me anything?
   Check that `CONTRIBUTING.md` matches how the project really works (branch to target, the exact
   test/lint commands and whether they run in a container, commit conventions, CI gates a PR must
   pass); that a contributor's local setup is documented separately from an end user's install if
   they differ; that `SECURITY.md` gives a real reporting channel; that the project states its
   maturity (alpha/beta/stable) and known limitations honestly; whether issue/PR templates and
   labels like `good first issue` exist (recommend them only if they'd actually be answered).
   Flag anything that only makes sense with access to my machine, my private repos or my Dibs
   instance.

7. **Release recommendation.** Whether this repo warrants a new tag/release now (docs drifted,
   fixes landed, features shipped since the last tag: `git describe --tags`, `git log
   <last-tag>..HEAD --oneline`) and what the release notes should cover. With no tag yet, say
   whether it is ready for a first prerelease and what blocks it.

### The recruiter/interviewer pass

One agent, over the résumé PDF (`pdftotext -layout <file> -`), the profile `README.md`, the
LinkedIn PDF (same `pdftotext`; read the page images too if the text drops the Featured cards), and
all in-scope repos as a reader meets them. It judges tone and weight across everything, so it runs on
the strongest model, over the other workers' compact findings and the excerpts they cite.

1. **Résumé ↔ profile README ↔ LinkedIn consistency.** Genuine contradictions in stack claims, dates,
   titles, years of experience, project descriptions, CI claims. Any exact test or assertion count
   in either document is a finding in its own right.
2. **Verify every technical claim against the repos and the atlases.** All three documents make
   checkable claims: "CI runs the suite against X and Y", "PHPStan/Rector/Pint/Peck gate every
   push", line counts, "no hostname, service, or credential exists anywhere in the code",
   coverage floors. Use the atlas for what exists, the CI YAML and phase 2 results for what runs.
   Report anything overstated, stale, or unverifiable, and say what you verified vs. inferred.
3. **The 30-second skim.** What impression does the profile README give, and separately what
   does LinkedIn give (headline wording and length, About opening, Featured cards with working
   links, images and non-truncated blurbs, experience dates against the résumé, how the page
   reads to a recruiter search)? Is the strongest
   evidence surfaced early? What's buried, redundant, or reads as filler/AI boilerplate?
4. **The engineer's read.** What impresses, what gives pause: README quality, commit message
   quality, test quality (not just count), architecture decisions and whether they're explained,
   whether the project looks maintained.
5. **Red flags.** Dead links, broken badges, stale/abandoned appearance, licence problems,
   over-claiming, personal information that shouldn't be public, unprofessional content.
6. **AI-tooling perception.** These repos were built with heavy AI assistance and the history
   shows it (co-author trailers, agent instruction files, commits authored by a bot rather than by
   me). Assess honestly how the *artifacts* read to a hiring manager, and whether the one-sentence
   disclosure on the profile is the right dosage, too defensive, or contradicted by what the repos
   show.

---

## Phase 4: findings and report

**Tool runs (only with the `tools` argument).** For each repo, in a detached worktree at the
origin tip (never in a checkout that is a running site), run the project's own documented
test/lint commands the way its CLAUDE.md says (usually inside its test container). The suite must
use an isolated test database, and the run must not take any real-world-visible action; if either
can't be guaranteed, skip that repo and say so. Say what I'm about to run and get my go-ahead
first. Without `tools`, rely on CI results from phase 2.

**Judgement.** The strongest model (Opus) ranks the workers' compact findings and the code
excerpts they cite, not the raw repos. Sonnet tends to grade too kindly; Opus is for catching what
a reader would actually weigh. Before relaying the top findings, spot-check the most severe claim
from each worker against the actual file: workers confidently report things that turn out to be
wrong.

**Findings shape.** One finding, one shape, shared with the atlas audit (`/feature-atlas`,
"Findings"): kind (`bug` | `docs drift` | `portfolio`), repo, atlas subsystem id, Verified-at SHA,
`file:line` with the quoted text, severity, and a suggested fix with options where there's a real
trade-off. Kind rules: a defect in the code is `bug`; a doc that disagrees with the code or atlas
is `docs drift`; anything that affects only how the repo reads to a hiring manager (leaks, tone,
buried stories, hygiene, README polish) is `portfolio`. Unverified items go in a separate
section, not filed.

**Filing.** Findings become ordinary Dibs tasks in the repo's Group, labelled with their kind,
under one `Job search audit: <date>` parent task. `todo_search` for an existing open task first
and update it instead of filing a duplicate. File nothing until I've decided (below): during the
run, workers' findings live in the report. The file-accounting list is kept in the parent task.

**File accounting.** Every report ends with the files actually looked at: each sampled file with
its subsystem id and why it was chosen (always, random, or unread glob), the whole-tree scans that
were run, and what was not read at all. A claim made about code that isn't on that list is
unverified. Calibrate occasionally: run one repo's audit on both models and diff the results; drop
the stronger model from a step where the cheaper one matches, keep it where it finds real issues.

**Launching workers.** Background subagents can hang forever on a permission prompt nobody sees.
When the `sessioneer` CLI is on PATH, launch each worker and the judge as a headless session
instead: `sessioneer --workdir <scratch dir> --model <sonnet|opus> --mode auto "<prompt>"`.
Always pass `--mode auto`. Put the long worker prompt in a file in the scratch dir and make the
launch prompt "read <file> and follow it" plus the per-repo parameters; have each worker write its
report to a file there, and `sessioneer --kill <name>` each session once its report is read. Use
`Agent` subagents only when `sessioneer` is unavailable. Workers use `git -C <path>` and absolute
paths, never `cd` compounds, and keep command output small (count with `-c`/`-l` rather than
printing hundreds of hits).

**Models and other tools.** Evidence gathering (phases 1-3 workers) is mechanical reading and
listing: use a mid-tier model (Sonnet) and have workers return about 300 words each. To save
Claude tokens, evidence gathering may run on Codex, Antigravity's `agy` or opencode instead, at
the model and reasoning level that suits the step (check what is installed and which models are
offered; never guess a name; launch details are in the `orchestrator-worker` skill's cross-tool
section). Outside Claude the no-edit rules are on the worker's honour, so give it the repo path and
the rules in the prompt and verify what comes back. Where one agent would both gather and judge,
split it into those two steps.

**Notes files.** After the report, and only for the résumé and LinkedIn, write the proposed wording
as notes for me to apply by hand (I edit the résumé and LinkedIn myself; the audit never touches
the ODT/PDF or LinkedIn):
- `~/Documents/andres/resume/current/php/resume-review-notes.md`: update the existing file in
  place, keep its structure (agreed direction, section-by-section proposed wording, already
  reflected, still pending, contact details), refresh stale facts and tips, and move items that
  are now done to "already reflected" instead of deleting them.
- `~/Documents/andres/resume/current/php/linkedin-review-notes.md`: same style, created if
  missing: agreed direction, then per LinkedIn section (headline, About, Featured, Experience,
  Skills, other) the current text, the proposed replacement, and why. Include the
  consistency fixes against the résumé and README, and the checklist of what to change by hand.
No exact test or assertion counts in proposed wording. These files hold proposals only, never
secrets, and nothing in them is final until I apply it.

**Report to me.** One consolidated, deduplicated, cross-repo priority list, highest impact first,
each item with why it matters *for the job search specifically*. Group anything that appears in
more than one repo (the same leak pattern, the same doc-drift class) so I fix it once everywhere.
Then the "already strong, don't touch" list and a per-repo release line. Say which items are
purely mechanical and which need a decision from me, present the decisions in one batch with a
recommendation each, and don't start fixing anything until I've picked.
