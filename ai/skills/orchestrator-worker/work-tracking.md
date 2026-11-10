# Work tracking, readable records and session disposition

Read this section before persistent work, Dibs bookkeeping or a final session disposition.
These procedures apply to every agent. Claude hooks implement conveniences and safety checks;
agents without hooks use MCP/CLI and verify the resulting claims and completion themselves.

## Intent, scope, claims and recovery

A persistent mutation changes lasting files, Git state, databases, services or external state.
Scratch-only writes do not count. Substantial work still requires tracking even if read-only;
quickly resolved read-only questions need no task. Before related work, find or create the fitting
task and claim it. Use temporary tasks for bounded ad hoc work and durable plans with steps for
multi-phase/cross-session work. Record goal, exact next step, workdir, branch and conversation id
before the first mutation. A private in-session todo list is not a claim or recovery record.

Never edit alongside another process’s live claim (`isCurrentlyAlive: true`); coordinate or choose
other work. Keep the capability token and heartbeat long work. Keep one editable checkpoint per
claim current from the start: a crash or quota cutoff may prevent an exit update. Classify any
automatically created temporary task under its correct project/parent before substantive work.
Expired/lapsed claims leave unfinished tasks, not completed work. Before taking over a dead
claim, read the previous claimant’s comments and transcript and record that you took over.

## Canonical identity

Use the local Dibs `id`, never its GitHub number or URL, wherever a record is identified. Use
the actual agent conversation id for sessions; an unambiguous eight-character prefix is fine.
Names may follow as labels, never replace ids. In messages to Andres, describe each id once at
first mention in about 5–10 words; group related ids and use bare ids thereafter. Dibs records
already link by id and need no repeated description. Repository content must not cite local task
ids; shared rule-library identifiers remain supported by its generated index.

Claim `agentName` is `<agent>:<session name>:<conversation id>`. Obtain the session name with
`sessioneer --whoami`; without Sessioneer use `unknown`. Claude may obtain its conversation id
from `CLAUDE_CODE_SESSION_ID`; other agents use their own real session ids. The first checkpoint
includes this identity, workdir and branch. Update claim identity when reassigning a session.

## Work lines and actual claims

Before related task work, output on its own line, outside code fences:

    [work <id or new> | <description> | <type>]

Types are `code`, `tests`, `docs`, `git`, `db`, `live-site`, `dibs`, `infra`, `research`; combine
them with `+`. With Claude hooks, an existing id is claimed or `new` creates and claims a temporary
task. The hook delivers rules for those types and may deny the first mutation while delivering
new rules: check them and retry. Reads/searches remain allowed. A denied mutation without a claim
asks for the declaration. Recovery after repeated denials, failure-open warnings or scratch/subagent
exemptions do not authorize skipping tracking. A parent holds the task for bounded in-process
workers; independent cross-tool/persona workers follow their assigned claim protocol.

Without hooks, declarations alone do nothing: use MCP/CLI to find/create/claim and verify ownership.
A prompt mentioning a task id alone is not proof of a claim. Follow late-delivered rules by checking
the triggering call and earlier work, then correcting anything missed.

## Lean, readable Dibs records

Update a finished or blocked plan step immediately: what changed, commit, next step, blocker and
why. Maintain the canonical plan body through optimistic `todo_revise`; comments hold concise
evidence/checkpoints, pass/fail and relevant errors, never raw logs. Put transient session state in
one temporary handoff, not in durable plan bodies. A cold session must recover from the records.

State belongs in existing fields, links and labels. Keep one living checkpoint per claim, edited
in place. Completion evidence belongs in `todo_complete`’s closing note. Never file a task/comment
whose only content is that a step became blocked/done. Before filing anything, search existing
open/closed records and comments with one or two plain keywords, then a synonym. Reuse/update
matching records. Automated jobs use idempotency keys, at most one task per violation and one
standing findings issue; close violation tasks when cleared.

Write full words with spaces between words/numbers, one idea per line, blank lines between
paragraphs, and bullets for lists. Say less rather than compressing sentences or joining words.
Identifiers, ids, paths and code remain exact. Peer messages/worker prompts may be terse.

## Filing and scope

Choose the actual area, one Group per project/site/topic and fitting parent; ask when genuinely
unsure rather than using catch-all buckets. On a project’s first item, create a lightweight parent
with repo path, stack and purpose. Ordinary bugs/backlog items are tasks; use `plan` only for genuinely
multi-step work. Priority is 1 highest through 5 lowest; leave it unset without a reason to rank it.

Explicit `Todo:`, `next:` and “after X, do Y” instructions are backlog notes: file them and continue
the current work. For self-discovered optional follow-ups, finish the request and follow rule 1077’s
decision before expanding scope or filing an unrequested task. A follow-up record includes project/
files, evidence, impact, unconfirmed facts and a concrete next step. Store durable gotchas in lesson/
research records promptly; check those records before research. Search titles, bodies and comments,
including closed records, using keywords then a synonym.

## Completion evidence and bookkeeping

Before a commit, search docs for old tool/argument/config/command names. Commit required docs/tests
with the code they describe. Fix later misses openly in follow-up commits; never rewrite pushed
history to hide a miss. At commit/merge/tag/release, update affected docs, the atlas hint, Latest release,
plans, notes and knowledge in the same step. Follow `git-workflow/atlas.md`: hint, never manual refresh.
Close finished tasks rather than leaving “done” notes; state actual merged SHA/tag and evidence.
Finish required housekeeping before reporting done. Name/file external blockers and put durable
lessons in lesson/research records instead of burying them on closed tasks.

With Claude hooks, place completion on its own unfenced line:

    [complete <id> | sha=<sha|"none: why"> tests="<passed command|none: why>" docs=<paths|"none: why"> | <summary>]

Evidence uses shell-style quoting; `docs` paths are comma-separated. A real commit must exist on the
current branch and required tests must pass before completion. Supply evidence required by the task
guard; honest `none: <reason>` values cover fields that do not apply. Only an explicit completion or
release ends work; temporary tasks survive dead sessions and are deleted only when completed/discarded.

Routine Claude bookkeeping may use one fenced `dibs` block at the reply end. Supported lines are
`claim <id>`, `note <id>: <text>` (edit the one checkpoint), `append <id> ## <Section>` followed by
indented content, `done <id> <evidence> :: <summary>`, and `atlas <subsystem>: <change>`. Append is
append-only; body restructuring uses `todo_revise`. A legacy claim block takes effect at Stop, so
do not rely on it for an earlier edit; use a work line first. A refused completion blocks once;
fix/resend, preserving unapplied lines. Already-applied lines are not repeated; results appear next
prompt. Use MCP/CLI after two refusals, for reads, record creation, body revisions and handoff/releases.
Agents without hooks do all bookkeeping through MCP/CLI and inspect actual results.

## Status, quota and handoff

Every FINAL reply, including workers/orchestrators, ends with exactly one status phrase from rule
1226. Parameterized statuses explain what/why, input needed, destination or wait dependency/time.
Do not append the phrase to every progress commentary. The orchestrator relays worker verdicts.

`Continue in this session`, `Waiting on Andres` and `Waiting on other work` may retain and renew
claims while this same session will act again. Ask pending questions through an available supported
question tool; otherwise put numbered questions at the reply’s end, followed by the required status.
Do not replace an unanswered decision with a Waiting line. Waiting on Andres also covers real-world
actions, review artifacts and future dates. Waiting on other work means this session must act after
that dependency; a replacement that can continue cold without it instead permits Safe to archive.

Before a `Continue in a different session` status, ask Andres with the question tool whether to
start that session now with the right prompt. On yes: file the handoff (`session-handoff`: state,
next steps, what Andres must do, cleanup, docs/atlas), release every claim, launch the new session
with a prompt naming the handoff id and telling it to verify the claims are free and this session is
archived before working, then archive this session. On no, end with the status line only.

Before Safe to archive or All planned work is done, complete/release claims, update records and
clean test resources. Continue in a different session requires a handoff then release. For unfinished
work that is being parked, create one temporary task labelled `handoff` using the `session-handoff`
body, give Andres its id, then release with what remains and the exact next step. Keep durable lessons/
decisions on permanent records. Disclose work done unclaimed in closing evidence.

Check `sessioneer --usage` before long work and periodically. At about 90% session or weekly quota,
start no new steps; finish or safely park the current one before exhaustion. Archive a replaced own
session only after it is idle, unclaimed and recoverable cold; never kill another agent’s active session.
Report which conversation ids were archived and which records/replacements continue them.

Claude’s stop gate checks the status first, then applies completion/bookkeeping, then examines claims.
If status was missing, repeat any completion/block lines with the corrected status. Archive/All-done/
transfer with claims blocks once; Continue-in-this-session/Waiting renews instead. Hook bypass/failure
warnings do not waive manual requirements for any agent.
