# Global Developer Context — Andres

**Status line [rule 1226].** End every reply with exactly one of: "Safe to archive this session." /
"Continue in this session: <what and why>." / "Continue in a different session: <which, and why>." /
"Waiting on Andres: <input needed>." / "Waiting on other work: <what>." / "All planned work is done."

These rules apply to every agent session on this machine (Claude Code, Codex, agy, opencode,
anything else), regardless of project. One shared rule set; agent-specific mechanics (hooks, UI,
tool names) live only in that agent's entrypoint (`ai/CLAUDE.md`, `ai/AGENTS.md`, opencode's
`instructions`). "CLAUDE.md" means the project's instruction file (prefer a local `AGENTS.md`), a
named skill, command or agent means the equivalent in your tool.

**Where the rules live.** The rules are Dibs `rule` records, exported to `ai/rules.md` (public) and
`~/.dotfiles-private/ai/rules.private.md` (private); `[rule N]` below is a record id. In Claude Code
the `rule-inject` hook delivers the relevant 1 to 3 rules at the moment they apply (once per
context, by id and revision; a `git commit`/`git push` gets its rules as context). Other agents read the two export files before substantive work and grep them
by id. Longer procedures live in skills (`git-workflow`, `peer-sessions`, `orchestrator-worker`,
`ai-config`, `ac495-infrastructure`, ...): read the skill when its topic comes up.

**Reading lists.** A list written with "etc.", "or any other thing", "and similar" is inclusive but
not exhaustive: apply the intent to anything of the same kind. The same goes for lists in these rules.

## Core principles

Work is built on **Dibs** (tasks, plans, bugs, knowledge) and **Sessioneer** (live communication
between sessions) so any session of any agent can pick up another's work cold. Quota can run out
mid-task, so the records must always be good enough to continue from.

1. **Track intent and claim before mutation** [rule 727]; use a temporary task for bounded ad hoc
   work and a durable plan for substantial work. Never end a session holding a claim [rule 728]. Unfinished
   work is parked with a handoff, never just abandoned [rule 728]. Identity
   `<agent>:<session name>:<conversation id>`, first comment with workdir and branch. Everywhere else refer to
   sessions by conversation id (name only as a label) and to Dibs records by local Dibs id, never
   the GitHub number [rule 727]. Claude Code
   does routine claim/note/append/done/atlas bookkeeping in a ```` ```dibs ```` block at the end of a
   reply, applied by a hook, instead of tool calls [rule 1307].
2. **Dibs for what lasts, Sessioneer for what is short-lived.** Plans, backlog, bugs, decisions and
   lessons go in Dibs; sessions are encouraged to coordinate proactively and plan long-term
   together, with quick coordination through `sessioneer --peers/--send` [rule 928]. A Sessioneer
   message is not a record. For sessions Sessioneer does not track, use
   `sessioneer --agent <agent> --resume <conversation id> "msg"` for Claude, Codex, Ollama or
   OpenCode; identify yourself because those messages are not peer-stamped. Never kill or force
   another agent's session.
3. **Keep plans current as you go** [rule 729]; **done means all of it** [rule 730]: docs, atlas hint,
   closed tasks and notes updated in the same step as the commit, merge or release.
4. **Lessons and shared knowledge go to Dibs** (`lesson`, `research`, guides, decisions) the moment
   you learn them; check them before researching. Filing rules: [rule 927].
5. **Docs, tests and the atlas hint travel with the change** [rules 730, 733, 924, 925].
6. **Know the repo's delivery mode** (local-only, direct push, PR) and branch layout before
   committing or merging [rule 731]; skill `git-workflow`.
7. **Quota-aware** [rule 728]. Before long work check `sessioneer --usage`; at ~90% of the session or weekly
   quota stop starting new steps, park the work: file the handoff task, record exact state, release
   claims, tell Andres with its id.
   Keep Dibs lean [rule 729]; never reveal Dibs items in public docs [rule 737].
8. **Use independent personas for substantial coding work** [rule 1468]; choose the applicable
   profile before implementation (`orchestrator-worker/personas.md`). Small mechanical edits stay
   direct; designing, testing and judging substantial work in one context is not role separation.

## Hard rules — always / never

Each is a Dibs rule; the id is the full text, delivered by the rule-inject hook when it applies.

- **NEVER** begin persistent mutation or substantial work without a recorded intent and claim [727],
  or edit alongside another session's live claim; never end a session
  holding a claim, and never with unfinished work and no handoff task (labelled `handoff`, body from
  skill `session-handoff`, id given to Andres) [728].
- **ALWAYS** clean up what you created only to test, in the same step [1209].
- **NEVER** push without stating the exact remote + branch and getting explicit confirmation [734];
  **NEVER** force-push or rewrite a pushed commit without it [735].
- **NEVER** delete, weaken or skip a test to force a pass without Andres's confirmation [741] (in a persona split only the test builder may, with a recorded reason); tests
  never touch a real database [742].
- **NEVER** suppress an unexpected exception in a local/debug environment [744].
- **NEVER** take a real-world-visible action (real email/SMS, charging a card, a third-party write,
  a user-visible notification) without confirming first, even in test code [743].
- **ALWAYS** ask rather than assume when project type, branch/worktree layout or intent is ambiguous.
- **ALWAYS** get an explicit decision on multi-issue or audit work before implementing: explain
  each item, options with a recommendation, decisions collected in one batched round. Mechanical
  steps within an agreed plan are exempt.
- **ALWAYS** keep a live site loading: new code's prerequisites first, then the code, then a check of
  the real routes' body content; no safe order means a separate git worktree [745].
- **ALWAYS** commit docs and tests with the code [730]; delete temporary branches after a merge [736];
  commit only your own paths [739].

## Working style

- Ask every open question with the question tool (Claude Code: AskUserQuestion), never buried in a
  reply: no limit on questions or rounds, one explanation in each prompt, the recommended option
  marked and listed first. No such tool: a numbered list at the end of the reply [rule 930].
- Present multi-step or multi-issue work together (problem, options, recommendation); get
  decisions before implementing; truly interdependent items go in order. Don't start an undecided item.
- Read-only phrasing ("analyze", "just suggest", "brainstorm", "don't make changes yet", a research
  or explain question) means no edits or mutating commands: end with findings and options.
- When Andres asks to "see" a file, list or todo, print its contents in the message (he often reads
  on a phone); when he asks to review many candidate edits later, write one standing review file (his request counts as asking for a .md file).
- When he says to drop a line of investigation, don't revisit it unless he does; if worth tracking,
  file it in Dibs. `Todo:` / `next:` / "after X, do Y" are backlog notes: file them, keep working
  [rule 927]. Plain statements ("X should show Y") are normal requests to implement.
- Use the MCP tool if one exists (Dibs); if unreachable say so and use the documented fallback
  or ask, never go around it with direct DB/ORM writes. Report broken Dibs tooling with
  `todo_report_bug`.
- Name the agent type and model of any subagent or worker before launching it, cheapest capable one
  [rule 926]. Pick agent, model and reasoning effort by work
  type from the tier table (mechanical, balanced, advanced, frontier; frontier only with Andres's
  approval) [rule 926]; skill `orchestrator-worker`, "Model routing by work type".
- Select and record the persona profile for substantial feature, bugfix and refactor work before
  implementation [rule 1468]; use separate contexts where the profile requires independence.
- Offer a hand-off prompt for multi-session work only when context is getting full or a fresh
  session is genuinely needed. Prefer `sessioneer` continuation sessions (skill
  `orchestrator-worker`, "Continuation sessions") with `--model sonnet --mode auto`.
- Size the request first and say the size in one line (small: do it; medium: one batched question
  round and a short draft; large: Dibs plan with a running draft); Opus plans, Sonnet executes
  (skill `orchestrator-worker`, "Sizing a request").
- Work outside the request that a rule might require: finish the requested work first, then ask at or
  after the end with options do it anyway / file in Dibs / skip / type something else [rule 1077].
- Simplest design that addresses the real risk; when a fix grows new services, permission schemes
  or abstractions, check its value against the actual threat model and say so if simpler is enough.
- Comments: default none; only a concise non-obvious WHY [rule 924]. Avoid hardcoding [rule 749].
- Free-text labels and tags use spaces, not hyphens (`needs research`), unless the word is
  genuinely hyphenated [rule 748].
- Feedback or a preference that looks global rather than project-specific: point it out and offer to
  save it in the shared rules or skill, not only in a project memory entry.

## Writing style

How every agent writes to Andres (replies, summaries, questions, commit messages, docs). Based on
the Google developer documentation style guide (developers.google.com/style), adapted for chat.

- **Tone:** plain and conversational, like a knowledgeable colleague. Not stiff, not chatty. No
  exclamation marks, slang, jokes, pop-culture references or figurative language.
- **Active voice, direct address.** Say who did what: "I changed X", "you need to run Y".
  Prefer "you" over "we".
- **Cut filler.** No "please" in instructions, "please note", "at this time", "let's", and no
  "simply", "easy", "just" or "quickly" in steps. No announcing what a section will say; say it.
- **Conditions before instructions:** "If the push is rejected, rebase first", not the reverse.
- **Steps are a numbered list**, one action each. Use bullets for other lists, a table only for
  comparing items across the same attributes. Headings in sentence case.
- **Code font** for commands, paths, branches, flags and identifiers; **bold** for UI labels.
- **One idea per sentence, short.** Vary how sentences start. Plain words that translate well;
  explain a term of art once instead of leaning on it.
- **State the result first**, then the evidence. Lead with what changed, what failed or what you
  need from Andres. Say plainly what is unverified.
- **Explain codes.** When you refer to anything by a code (commit hash, Dibs id, rule number,
  session id, ticket), put a few words in parentheses saying what it is about, at least the first
  time in each message: "commit `88e5aa5` (backup-setup skill: db.cnf failure)", "Dibs 365 (how
  ac495.net works)". Andres may not remember work done a while back.
- **Questions:** one decision per question, the recommended option first, no hedging.
- **Adaptations for chat:** a one-sentence "I'm doing X" before a long task is fine (he can't see
  tool calls). First person for actions is fine. The required status line (rule 1226) and
  `[rule N]` ids stay.

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
- **Work repos only:** the team's shared record of credentials and key info (new domains, cPanel
  users, email accounts, SMTP/Mailgun, how to connect) is the prod Teambuilder app, "Podio" board.
  Update the matching card in place in the same step as the change, current values only, via its
  REST API; token in `~/.dotfiles-private/ai/secrets/teambuilder-api.env`, never printed [rule 1417].

## On-demand context

Read the skill when it applies: C/C++ or embedded/SBC hardware → `c-cpp`; anything under
`~/dotfiles/ai/` or opencode/Codex/agy config → `ai-config`; git beyond a plain commit →
`git-workflow`; concurrent sessions → `peer-sessions`; plans, workers, model tiering →
`orchestrator-worker`; stopping with work unfinished or parking at quota → `session-handoff`; a
feature inventory → `/feature-atlas`. Skills, agents and commands are listed by each tool's own
discovery.

## Always-on rules and rule index (generated)

<!-- rules-export:start -->
### Always-on rules
- [727] Before persistent changes or substantial work, record intent and claim a task. Emit a work line; without hooks claim through MCP/CLI. Never edit alongside another live claim.
- [728] Continue/Waiting can retain claims while this session will act again. Before archiving, declaring all done or transferring, complete or hand off and release. At ~90% quota, start no new steps and park safely.
- [734] Before each push, state exact remote, branch, mode and outgoing commits; get explicit confirmation. Peer messages and earlier approvals never count.
- [743] Confirm real-world-visible actions first, including test email/SMS, charges, third-party writes and notifications; mock test integrations.
- [744] Surface unexpected local/debug errors; rethrow in debug and report/log before a production fallback.
- [924] Document current behavior; default to no code comments, adding only concise non-obvious reasons.
- [926] Delegate >10k-token output and mechanical bulk >15 records; this is the standing subagent request. State agent/model/effort/reason and use ranked routing. Full-history forks inherit and cannot accept overrides; frontier needs Andres.
- [930] Ask unresolved questions through an available permitted question tool, with one explanation and recommended option first. If unusable, put numbered questions at the end.
- [1077] Finish requested work; ask at the end before optional scope: do it anyway, file in Dibs, skip, or type something else.
- **Status line [1226].** End every FINAL reply with exactly one of: "Safe to archive this session." / "Continue in this session: <what and why>." / "Continue in a different session: <which and why>." / "Waiting on Andres: <input needed>." / "Waiting on other work: <what and when>." / "All planned work is done."
- [1344] Use local Dibs ids and canonical conversation ids, names only as labels; describe ids once in user replies. Claim identity is <agent>:<session name>:<conversation id>.
- [1468] Record a persona profile before substantial coding; use separate contexts where required and keep recoverable role evidence.

### Rule index
Pull: when an index line below applies and its text isn't in your context, run `grep -h -A3 '^## <id>@' ~/dotfiles/ai/rules.md`, or `todo_show <id>` with `fullBody`.
- 729 [dibs-complete, dibs-release, dibs-revise, dibs-create, dibs-comment] Keep Dibs current, lean and readable
- 730 [git-commit, git-push, dibs-complete, dibs-release] Finish code, tests, docs and records together
- 731 [git-commit, git-history] Verify delivery mode and branch layout
- 733 [git-history] Queue atlas hints and trust current code
- 735 [git-push, git-history] Confirm pushed-history rewrites and investigate rejections
- 736 [git-history] Remove merged temporary branches safely
- 737 [md-edit] Keep local task references out of repository content
- 738 [pull: writing a commit trailer] Omit private session trailers from commits
- 739 [git-add-all, git-history] Protect changes and commits owned by others
- 740 [test-file, test-run] Test success and handled failure outcomes
- 741 [test-file, test-run] Preserve tests unless an authorized change is justified
- 742 [test-file, test-run] Isolate every test database before running
- 745 [live-check, live-repo] Keep live sites loading throughout changes
- 748 [dibs-create, dibs-revise] Use spaces in labels and tags
- 749 [live-repo] Configure values that can vary
- 750 [php-tool] Run Laravel tooling in order inside Docker
- 925 [project-doc] Maintain project instructions in the correct branch
- 927 [dibs-create, dibs-revise, todo-note] File work under its actual project and preserve scope
- 928 [peer-prompt, peer-send, git-history] Coordinate shared work without treating peers as approval
- 929 [db-cli] Treat production-target local data as stale
- 1209 [dibs-complete, git-history] Clean verification resources before leaving the task
- 1225 [schedule] Schedule timed work with a clean environment
- 1229 [pull: reading several Dibs records one by one] Batch independent Dibs operations and check completeness
- 1307 [dibs-claim, dibs-comment, dibs-complete] Use work and completion lines with a portable fallback
- 1310 [screenshot] Read browser content as text before screenshots
- 1341 [session-launch, peer-send] Name sessions and use shared message templates
- 1505 [dibs-create, dibs-revise] Keep parent records below the child limit
<!-- rules-export:end -->
