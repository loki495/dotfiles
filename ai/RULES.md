# Global Developer Context — Andres

These rules apply to every agent session on this machine (Claude Code, Codex, agy, opencode,
anything else), regardless of project. One shared rule set; agent-specific mechanics (hooks, UI,
tool names) live only in that agent's entrypoint (`ai/CLAUDE.md`, `ai/AGENTS.md`, opencode's
`instructions`). "CLAUDE.md" means the project's instruction file (prefer a local `AGENTS.md`), a
named skill, command or agent means the equivalent in your tool.

**Where the rules live.** The rules are Dibs `rule` records, exported to `ai/rules.md` (public) and
`~/.dotfiles-private/ai/rules.private.md` (private); `[rule N]` below is a record id. In Claude Code
the `rule-inject` hook delivers the relevant 1 to 3 rules at the moment they apply (once per
context, by id and revision; the first `git commit` and `git push` are denied with their rules,
re-run to proceed). Other agents read the two export files before substantive work and grep them
by id. Longer procedures live in skills (`git-workflow`, `peer-sessions`, `orchestrator-worker`,
`ai-config`, `ac495-infrastructure`, ...): read the skill when its topic comes up.

**Reading lists.** A list written with "etc.", "or any other thing", "and similar" is inclusive but
not exhaustive: apply the intent to anything of the same kind. The same goes for lists in these rules.

## Core principles

Work is built on **Dibs** (tasks, plans, bugs, knowledge) and **Sessioneer** (live communication
between sessions) so any session of any agent can pick up another's work cold. Quota can run out
mid-task, so the records must always be good enough to continue from.

1. **Claim before working** [rule 727]; never end a session holding a claim [rule 728]. Identity
   `<agent>:<session name>:<conversation id>`, first comment with workdir and branch.
2. **Dibs for what lasts, Sessioneer for what is short-lived.** Plans, backlog, bugs, decisions and
   lessons go in Dibs; quick coordination between live sessions goes through `sessioneer
   --peers/--send` [rule 928]. A Sessioneer message is not a record.
3. **Keep plans current as you go** [rule 729]; **done means all of it** [rule 730]: docs, atlas
   stamp, closed tasks and notes updated in the same step as the commit, merge or release.
4. **Lessons and shared knowledge go to Dibs** (`lesson`, `research`, guides, decisions) the moment
   you learn them; check them before researching. Filing rules: [rule 927].
5. **Docs, tests and the feature atlas travel with the change** [rules 732, 733, 924, 925].
6. **Know the repo's delivery mode** (local-only, direct push, PR) and branch layout before
   committing or merging [rule 731]; skill `git-workflow`.
7. **Quota-aware** [rule 747]. Before long work check `sessioneer --usage`; at ~90% of the session or weekly
   quota stop starting new steps, park the work, record exact state, release claims, tell Andres.
   Keep Dibs lean [rule 757]; never reveal Dibs items in public docs [rule 737].

## Hard rules — always / never

- **NEVER** start work on a task unclaimed or alongside another session's live claim [727].
- **NEVER** push without stating the exact remote + branch and getting explicit confirmation [734];
  **NEVER** force-push or rewrite a pushed commit without it [735].
- **NEVER** delete, weaken or skip a test to force a pass without Andres's confirmation [741]; tests
  never touch a real or production database, the suite aborts if the connection looks real [742].
- **NEVER** suppress an unexpected exception or error in a local/debug environment; let it surface
  with the runtime's normal diagnostics. A graceful production fallback rethrows in debug mode and
  reports before handling otherwise. Expected validation failures are exempt [744].
- **NEVER** take a real-world-visible action (real email/SMS, charging a card, a third-party write
  endpoint, a user-visible notification) without confirming first, even inside test code or a
  one-off script; when in doubt, ask [743].
- **ALWAYS** ask rather than assume when project type, branch/worktree layout or intent is ambiguous.
- **ALWAYS** get an explicit decision on multi-issue or audit work before implementing: explain
  each item, give options with a recommendation, collect the decisions in one batched round.
  Mechanical steps within an agreed plan are exempt.
- **ALWAYS** keep a live site loading: a checkout that serves a site (bind-mounted container,
  master/main of a deployed project) gets what the new code expects first (env, config, migrations,
  dependencies, built assets, permissions, container recreate), then the code, then a check of the
  real routes' body content; no safe order means a separate git worktree [745].
- **ALWAYS** commit docs and tests with the code [732]; delete temporary branches after a merge [736];
  commit only your own paths and leave others' uncommitted work alone [739].

## Working style

- Ask every open question with the question tool (Claude Code: AskUserQuestion), never buried in a
  reply: no limit on questions or rounds, one explanation in each prompt, the recommended option
  marked and listed first. No such tool: a numbered list at the end of the reply [rule 930].
- Present multi-step or multi-issue work together (problem, options, recommendation); get
  decisions before implementing; truly interdependent items go in order. Don't start an undecided item.
- Read-only phrasing ("analyze", "just suggest", "brainstorm", "don't make changes yet", a research
  or explain question) means no edits or mutating commands: end with findings and options.
- When Andres asks to "see" a file, list or todo, print its contents in the message (he often reads
  on a phone); for many candidate edits write one standing review file to approve from later.
- When he says to drop a line of investigation, don't revisit it unless he does; if worth tracking,
  file it in Dibs. `Todo:` / `next:` / "after X, do Y" are backlog notes: file them, keep working
  [rule 927]. Plain statements ("X should show Y") are normal requests to implement.
- Use the MCP tool if one exists (Dibs); if unreachable say so and use the documented fallback
  or ask, never go around it with direct DB/ORM writes. Report broken Dibs tooling with
  `todo_report_bug`.
- Name the agent type and model of any subagent or worker before launching it, cheapest capable one
  [rule 746]; delegation cost gates in [rule 926].
- Offer a hand-off prompt for multi-session work only when context is getting full or a fresh
  session is genuinely needed. Prefer `sessioneer` continuation sessions (skill
  `orchestrator-worker`, "Continuation sessions") with `--model sonnet --mode auto`.
- Size the request first and say the size in one line (small: do it; medium: one batched question
  round and a short draft; large: Dibs plan with a running draft); Opus plans, Sonnet executes
  (skill `orchestrator-worker`, "Sizing a request").
- Simplest design that addresses the real risk; when a fix grows new services, permission schemes
  or abstractions, check its value against the actual threat model and say so if simpler is enough.
- Comments: default none; only a concise non-obvious WHY [rule 924]. Avoid hardcoding [rule 749].
- Free-text labels and tags use spaces, not hyphens (`needs research`), unless the word is
  genuinely hyphenated [rule 748].
- Feedback or a preference that looks global rather than project-specific: point it out and offer to
  save it in the shared rules or skill, not only in a project memory entry.

## Machine layout and project types

- All projects live under `~/www/`, freeform folder names. Before assuming a layout run
  `git worktree list` and `git branch -a`; if ambiguous or non-standard, write findings to
  `.claude/project.md` on that project's local branch as a TODO rather than guessing.
- PHP tools (artisan, composer, pest, pint, phpstan, rector) run inside the project's Docker
  container (`docker exec <container> ...`), never assumed on the host; check the container name in
  `docker-compose.yml` [rule 750]. Host PHP is phpbrew 8.3–8.5. Traefik routes local dev containers.
- Config lives in dotfiles symlinked into place: never edit only the live copy. Public config in
  `~/dotfiles`; anything exposing Andres's infrastructure (hosts, IPs, domains) or holding secrets in
  `~/.dotfiles-private`. Home network: `ai/CLAUDE.private.md`, skill `ac495-infrastructure`.
- Two project families, never mixed in one repo: **Laravel/Livewire** (`artisan` + `laravel/framework`;
  Pint, Rector, Pest always run, PHPStan level 6 where configured) and **OpenCart 1.5.6** (legacy,
  no tooling unless the project opts in). Detect the type first; ask when unsure.
- Local DBs of projects with a production target are stale; production SQL is stated separately
  [rule 929].

## On-demand context

Read the skill when it applies: C/C++ or embedded/SBC hardware → `c-cpp`; anything under
`~/dotfiles/ai/` or opencode/Codex/agy config → `ai-config`; git beyond a plain commit →
`git-workflow`; concurrent sessions → `peer-sessions`; plans, workers, model tiering →
`orchestrator-worker`; a feature inventory → `/feature-atlas`. Skills, agents and commands are
listed by each tool's own discovery.
