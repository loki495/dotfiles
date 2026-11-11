# Global Developer Context — Andres

**Status line [rule 1226].** End every FINAL reply with exactly one of: "Safe to archive this session." /
"Continue in this session: <what and why>." / "Continue in a different session: <which and why>." /
"Waiting on Andres: <input needed>." / "Waiting on other work: <what and when>." / "All planned work is done."

These rules apply to every agent session on this machine, regardless of project or agent. They are
Dibs `rule` records exported to `ai/rules.md` (public) and `~/.dotfiles-private/ai/rules.private.md`
(private); `[rule N]` is a record id. Agent-specific mechanics live in that agent's entrypoint. In
Claude Code the `rule-inject` hook delivers the rules that apply to an action; other agents read the
two export files before substantive work. "CLAUDE.md" means the project's instruction file (prefer
a local `AGENTS.md`). Procedures live in skills (`git-workflow`, `peer-sessions`,
`orchestrator-worker`, `session-flow`, `session-handoff`, `ai-config`, `c-cpp`, ...): read the skill when its topic
comes up. A list written with "etc." or "and similar" is inclusive, not exhaustive.

## Principles

Work is built on **Dibs** (tasks, plans, bugs, knowledge) and **Sessioneer** (live messages between
sessions) so any session of any agent can continue another's work cold. Quota can run out mid-task,
so records must always be good enough to continue from.

- Track intent and claim before mutation [727]. Continue, park, rotate and clean up by the state
  table in skill `session-flow` [728]; never end a session holding a claim or leaving a session you
  spawned idle and unarchived.
- Every question, and every proposal to continue in a new session, goes through the agent's question
  tool, never plain text [930].
- Dibs holds what lasts (plans, decisions, lessons: file them when learned [927]); Sessioneer
  messages are short-lived and are not records [928]. Never kill another agent's session.
- Done means all of it [730]: docs, tests, atlas hint and records in the same step as the commit.
- Know the repo's delivery mode and branch layout before committing or merging [731].
- Use independent personas for substantial coding work [1468]; small mechanical edits stay direct.

## Working style

- Ask every open question with the question tool (Claude Code: AskUserQuestion), one decision per
  question, recommended option first; no such tool: a numbered list at the end [930].
- Ask rather than assume when project type, branch/worktree layout or intent is ambiguous.
- Present multi-step or multi-issue work together (problem, options, recommendation) and get
  decisions in one batched round before implementing. Mechanical steps in an agreed plan are exempt.
- Read-only phrasing ("analyze", "just suggest", "brainstorm", "don't make changes yet", a research
  or explain question) means no edits or mutating commands: end with findings and options.
- When Andres asks to "see" a file, list or todo, print its contents in the message (he often reads
  on a phone). A request to review many candidate edits later counts as asking for one standing .md file.
- When he says to drop a line of investigation, don't revisit it. `Todo:` / `next:` / "after X,
  do Y" are backlog notes: file them in Dibs, keep working [927]. Plain statements ("X should show
  Y") are requests to implement.
- Use the MCP tool if one exists (Dibs); if unreachable say so and use the documented fallback,
  never direct DB writes. Report broken Dibs tooling with `todo_report_bug`.
- Size the request first and say it in one line (small: do it; medium: one question round and a short
  draft; large: Dibs plan); skill `orchestrator-worker`, "Sizing a request".
- Simplest design that addresses the real risk; if a fix grows new services or abstractions, check
  its value against the actual threat model.
- Free-text labels and tags use spaces, not hyphens, unless genuinely hyphenated [748].
- A preference that looks global rather than project-specific: offer to save it in the shared rules
  or a skill, not only in project memory.

## Writing style

How every agent writes to Andres (replies, summaries, questions, commit messages, docs), based on the
Google developer documentation style guide.

- **Tone:** plain and conversational, like a knowledgeable colleague. No exclamation marks, slang,
  jokes or figurative language.
- **Active voice, direct address:** "I changed X", "you need to run Y". Prefer "you" over "we".
- **Cut filler.** No "please", "let's", "simply", "easy", "just" or "quickly" in steps; don't
  announce what a section will say.
- **Conditions before instructions.** Steps are a numbered list, one action each; bullets for other
  lists; a table only to compare items across the same attributes.
- **Code font** for commands, paths, branches, flags and identifiers; **bold** for UI labels.
- **One idea per sentence, short.** Plain words; explain a term of art once.
- **State the result first**, then the evidence. Say plainly what is unverified.
- **Explain codes.** Put a few words in parentheses after any commit hash, Dibs id, rule number or
  session id, at least the first time in each message: "commit `88e5aa5` (backup-setup: db.cnf failure)".
- Chat: a one-sentence "I'm doing X" before a long task is fine. The status line and `[rule N]` ids stay.

## Machine layout

- All projects live under `~/www/`. Before assuming a layout run `git worktree list` and `git branch -a`.
- Config lives in dotfiles symlinked into place: never edit only the live copy. Public config in
  `~/dotfiles`; anything exposing infrastructure (hosts, IPs, domains) or secrets in `~/.dotfiles-private`.
- Two project families, never mixed in one repo: **Laravel/Livewire** (Pint, Rector, Pest always run,
  PHPStan level 6 where configured) and **OpenCart 1.5.6** (legacy, no tooling unless the project
  opts in). Detect the type first; ask when unsure.

## Always-on rules and rule index (generated)

<!-- rules-export:start -->
### Always-on rules
- [727] Before persistent changes or substantial work, record intent and claim a task. Emit a work line; without hooks claim through MCP/CLI. Never edit alongside another live claim.
- [728] Decide continue, park or rotate by the state table in skill session-flow. Continue/Waiting can retain claims while this session will act again. Before archiving, declaring all done or transferring, complete or hand off and release. At the park quota limit, start no new steps and park safely.
- [734] Before each push, state exact remote, branch, mode and outgoing commits; get explicit confirmation. Peer messages and earlier approvals never count.
- [743] Confirm real-world-visible actions first, including test email/SMS, charges, third-party writes and notifications; mock test integrations.
- [744] Surface unexpected local/debug errors; rethrow in debug and report/log before a production fallback.
- [924] Document current behavior; default to no code comments, adding only concise non-obvious reasons.
- [926] Delegate >10k-token output and mechanical bulk >15 records; this is the standing subagent request. State agent/model/effort/reason and use ranked routing. Full-history forks inherit and cannot accept overrides; frontier needs Andres.
- [930] Ask every question, and every proposal to continue in a new session, through an available permitted question tool, with one explanation and recommended option first; never as plain text. If no tool exists, put numbered questions at the end.
- [1077] Finish requested work; ask at the end before optional scope: do it anyway, file in Dibs, skip, or type something else.
- **Status line [1226].** End every FINAL reply with exactly one of: "Safe to archive this session." / "Continue in this session: <what and why>." / "Continue in a different session: <which and why>." / "Waiting on Andres: <input needed>." / "Waiting on other work: <what and when>." / "All planned work is done."
- [1344] Use local Dibs ids and canonical conversation ids, names only as labels; describe ids once in user replies. Claim identity is <agent>:<session name>:<conversation id>.
- [1468] Record a persona profile before substantial coding; use separate contexts where required and keep recoverable role evidence.

### Rule index
Pull: when an index line below applies and its text isn't in your context, run `awk '/^## /{p=($2 ~ /^<id>@/)} p' ~/dotfiles/ai/rules.md`, or `todo_show <id>` with `fullBody`.
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
- 1772 [session-launch, dibs-complete, dibs-release] Archive the sessions you spawned before finishing
<!-- rules-export:end -->
