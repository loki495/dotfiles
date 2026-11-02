# Phases 1-3: atlas facts, tool checks, reader lenses, recruiter/interviewer pass

Reference for the `job-search-audit` command; read it at the step the command names.

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
7. **The verdict: CALL BACK / MAYBE / PASS** for a senior/lead PHP/Laravel role, given separately
   by three readers: a recruiter doing a 30-second skim of LinkedIn + profile README + résumé; a
   hiring manager who opens the top repos; a senior engineer doing a pre-interview technical
   screen. For each: the verdict, the 3 strongest reasons, the 3 weakest, and 1-2 changes that
   would raise it a notch. Then one overall paragraph. Candid, every reason cited to evidence
   (a file, a link, a line of the README), no softening.
