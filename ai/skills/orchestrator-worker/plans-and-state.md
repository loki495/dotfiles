# Plans, Dibs state, research and lessons

Reference for the `orchestrator-worker` skill; read it when the decision tree in `SKILL.md` points here.

## When This Applies

Two separate thresholds — don't conflate them. Crossing the first doesn't mean
crossing the second.

**Create a plan** (a `plan`-labeled issue in Dibs, via `todo_scaffold_plan`) when the task is:

- explicitly multi-phase, an audit, or framed as a plan/todo list by the user;
- expected to span more than one session (paused and resumed later, possibly by a
  different session or tool);
- work I would already reach for the in-session `TodoWrite` tool for, **and** it
  needs to survive a session boundary rather than just this conversation.

Skip Dibs for single-turn, single-file, quickly-resolved work — a plain reply
or an ordinary `TodoWrite` list is enough, and scaffolding a plan for a three-line fix
is pure overhead. When genuinely unsure whether a task clears this bar, err toward
creating the plan — cheap to create (one `todo_scaffold_plan` call), cheap to leave
nearly empty, expensive to reconstruct provenance for later if skipped and the task
turns out to run long.

**Escalate to full delegation** (spawn workers, apply
[Model Tiering](model-routing.md#model-tiering), consider parallel execution) once a plan is
underway, when:

- the work is expected to need a large tool-call/context footprint (many files, a
  test suite run, broad exploration) — see the growth-cost argument in
  [Model Tiering](model-routing.md#model-tiering);
- there are genuinely independent subtasks that could run in parallel;
- a cheaper model is plausibly capable of a bounded piece of the work and the cost
  difference is worth the coordination.

This should happen **automatically when it's clearly warranted, or with one quick
check-in when it's ambiguous** — never silently. If a plan turns out to need
delegation partway through, that's normal; nothing about the plan issue changes,
only how heavily its comments/claims get used (see [Project State](plans-and-state.md#project-state) —
every plan is a real Dibs issue from creation, light or not).

A plan that never needs delegation is not a failure of the protocol — most solo
work, once it clears the "create a plan" bar, stays solo the whole way through.

## Project Isolation

All project work happens inside the designated project directory. Do not create or
modify files outside it. External data may be read when the project needs it, but
treat it as read-only unless the project explicitly requires otherwise. Never modify
unrelated files, repositories, configuration, credentials, or user data.

## Project State

A project's multi-step work lives in **Dibs** — the personal MCP-backed task
tracker (`~/www/dibs`) — instead of local plan files. Reach it through
the `dibs` MCP server (registered at user scope for Claude Code as of 2026-09-13;
register it the same way in any other tool's own MCP config before relying on it
there — `claude mcp list`/that tool's equivalent shows whether it's connected) or,
when a tool can't reach MCP directly, the `todo:agent:*` CLI fallback:
`docker compose -f ~/www/dibs/docker-compose.yml exec -T -u www-data app
php artisan todo:agent:<command>`. Call `todo_status` (or `todo:agent:list`) once per
session to confirm connectivity before relying on it further.

A **plan** is a `plan`-labeled issue in Dibs; its **tasks** are that issue's child
issues, created together via `todo_scaffold_plan` (one atomic call: plan + all
initial children) or added individually afterward with
`todo_create(parentId: <plan issue id>)`. Each task's own local Dibs id/number is its
task ID — already stable, and what every other tool call keys on (`todo_show`,
`todo_claim`, `todo_revise`, `todo_comment`).

**Before starting work that might already have a plan, always check first** — don't
assume this is a fresh start:

1. Call `todo_context` (areas/Groups/labels/live-claims overview) and `todo_list`
   (filter `label=plan`, scoped to the Group matching this project/website if one
   exists) to find an existing, unfinished plan for this objective.
2. If a matching open plan exists, ask which to resume rather than assuming — then
   `todo_show` the plan issue and its children to read current state. A new session
   has no memory of the old one; Dibs is the authoritative record, the same reason
   this was file-based before.
3. Only scaffold a new plan for a genuinely distinct objective.

**Placement**: file the plan under the Project area (Work / Personal Projects /
Learning & Self-Improvement / Random Tasks) and Group (website/topic) matching the
current project — `todo_context` shows existing Groups; `todo_create`'s
`newGroupName` makes one if none matches yet. **If it's genuinely unclear which
Project area this belongs under** (most often Work vs. Personal Projects), **ask**
rather than guess.

There's no separate registry file to keep in sync — `todo_list`/`todo_show` always
reflect current state directly. Multiple plans can run concurrently across
different Groups/areas without needing any coordination file at all; if two plans
would touch the same project files, that's a sign they should be one plan or
sequenced, the same judgment call as before, just without an `INDEX.md` to check
first (`todo_list` filtered to `label=plan` serves the same purpose, live).

### Plan body

The plan issue's own body is the authoritative implementation plan — revise it with
`todo_revise` (optimistic-concurrency protected; a stale write comes back as a
non-error `{conflict: true, current: ...}` to reread and reconcile, never a silent
overwrite). It holds what `PLAN.md` used to: objective, decisions, dependency order,
current status, completion gates. Each task's own state stands in for a per-task
status field: `CLOSED` is done, an active `todo_claim_status` is in-progress, `OPEN`
with no claim is pending; use a `todo_comment` or the `waiting` label for a task
that's specifically blocked, since there's no dedicated status enum on an issue.

Do not close a task (`todo_complete`) merely because a worker (or direct work)
claims completion — the acceptance criteria in the plan body must actually be
satisfied first, exactly as before. That check is the orchestrator's job.

**Break the plan into child task issues as soon as its scope is known, decided
2026-09-13 — not only when delegating to workers.** A plan worked entirely solo,
inline, in one sitting still needs this: one `todo_create`/`todo_scaffold_plan` child
per concrete step, closed via `todo_complete` as each finishes. This is what makes
"what's left" a scannable checklist (`todo_show` the plan; open children are
remaining, closed ones are done) instead of something that has to be reconstructed by
rereading narrative comments. A prose-only progress comment ("done: X, Y; still need:
Z") is not a substitute — it decays the moment the list changes and nothing marks an
item complete. Add new child tasks the same way if scope grows mid-plan.

### Checkpoints, questions, and results

What `STATE.md`/`QUESTIONS.md`/`RESULT.md` used to separate are now all
`todo_comment` calls: on the **plan issue** for anything spanning the whole plan
(current step, worker model/mechanism/cost — see [Cost Reporting](roles-and-workers.md#cost-reporting) —
architectural decisions, known limitations, outstanding blockers), or on the
**specific task issue** for anything task-scoped (a blocker, a result, a
verification outcome — see [Worker Questions and Blockers](roles-and-workers.md#worker-questions-and-blockers)).
Post concise checkpoints, not a narration log — the same discipline the old files
required, now enforced by the same convention Dibs's own project already documents:
the issue body is the maintained canonical document, comments hold supporting
evidence and checkpoints.

**A tooling problem is not a plan question.** If a worker hits a bug, confusing
behavior, or unexpected error *in the Dibs MCP/CLI tooling itself* — not a plan
decision needing a human call — self-report it via `todo_report_bug` (`summary`,
`details`, optionally `toolOrCommand`/`arguments`) rather than working around it
silently or leaving it as an offhand comment. This lands in Dibs's own backlog
(labeled `agent report`) for later fixing, without blocking the plan on it unless it
actually does.

### Task claims

**Claude Code with the dotfiles hooks: use the ```` ```dibs ```` block [rule 1307].** Write
`dibs <id>` in the prompt or reply to claim before editing; put `note`, `append`, `done` and
`atlas` lines in a block at the end of the reply. The hook validates and applies them at Stop,
renews the claim on its own, and reports results on the next prompt, so none of the calls below
cost a turn. The MCP calls described in the rest of this section remain the path for other agents,
for workers without the hooks, and for anything the block refuses.

A worker claims its assigned task with `todo_claim` before starting — this replaces
marking a task `in_progress` in `PLAN.md`. Unlike a plain status field, a live claim
is bound to the worker's actual OS process and independently verified (host, pid,
process start time — see Dibs's own `docs/agent-interface.md` for the full model):
two workers genuinely cannot both claim the same task, and a claim whose process has
died becomes automatically recoverable on the next claim attempt, neither of which a
status field in a file could ever guarantee. `todo_claim` returns a capability token
— hold onto it; every subsequent `todo_heartbeat`/`todo_release`/`todo_complete` call
on that claim needs it.

Heartbeat (`todo_heartbeat`) periodically during a long task so the lease doesn't
expire out from under it — this creates no comment/push-queue noise, it's purely
local bookkeeping. On completion, `todo_complete` closes the task, optionally posts
a result summary as a comment, and releases the claim in one call — the worker's
completion report landing durably, not a separate step. Abandoning a task without
finishing it is `todo_release` instead, so another worker can pick it up immediately
rather than waiting out the lease. `todo_claim_status` reads a task's current claim
(if any) without needing to hold one yourself — useful for the orchestrator checking
in on a worker without interrupting it.

**Check claim status before starting any task — solo work too, not only delegated
workers, decided 2026-09-13.** Before touching a task's files (or resuming a plan at
all), `todo_claim_status` it — or check `todo_context`'s live-claims list. If it's
already claimed and `isCurrentlyAlive` is true, that's another live process (another
session, another tool, a parallel window) genuinely working on it right now — treat
it as off-limits. Skip to a different unclaimed task or plan instead of editing its
files, without asking Andres to confirm first (this is exactly the collision the
claim mechanism exists to prevent, so respecting it is the default, not a judgment
call each time). This matters because file edits happen immediately regardless of
which process made them — discovering unexplained uncommitted changes mid-plan is a
sign to check claim status before assuming anything, not to overwrite or "helpfully"
finish someone else's in-progress edit.

### Scratch work

Session hand-offs use `todo_create(temporary: true)` in the project's area and Group,
labelled `handoff`, parented to its permanent plan when one exists. Keep durable decisions and
progress on the plan; put transient resume state in the temporary task instead of a plan-body
rewrite or a committed hand-off file. The receiving session reads and claims it,
preserves any durable findings, then completes it to delete it permanently. Consume
temporary children first. Ordinary release retains it; `reason: NOT_PLANNED` discards
it. Completion summaries copied to a permanent parent follow that parent's mirroring
policy, so omit private details. Temporary tasks are excluded from durable plan and
atlas accounting and reconciler evidence checks. The body template, the receiver
protocol and the discovery query (`todo_list label=handoff state=OPEN`) live in skill
`session-handoff`; the `/handoff` command runs the same procedure and prints the
paste-ready prompt.

Exploration notes, one-off scripts, and temp diffs that support a plan but aren't
meant to become permanent records still don't belong in Dibs — keep them in the
session's own scratchpad directory, same as any other throwaway working file. Dibs
holds the plan/task/checkpoint record, not scratch files.

### Completion

A plan is done once every task is closed via `todo_complete` with satisfied
acceptance criteria. `todo_revise` the plan issue's body to reflect final status,
then close the plan issue itself the same way `closeIssue`/`todo_complete` closes any
issue. No separate archiving step: a closed issue already reads as done and stays
discoverable via `todo_list(state: 'ALL')` or a direct `todo_show`, the same way any
completed issue does — nothing to move.

## Shared Research Cache

Investigative findings that outlive any single plan — about a specific codebase, or
general technical facts (a library's behavior, an API's shape, a format's quirks) —
live as `research`-labeled issues in **Dibs**, not `.ai/research/` files, so the
next plan, any plan, any project, any tool, doesn't re-investigate something already
answered. File these under Personal Projects → the "AI workflows" Group (check
`todo_context` for its exact id; it already exists for cross-cutting agent/tooling
knowledge) unless the finding is specific to one project's own business domain, in
which case file it under that project's own Group instead.

An issue's title is the topic; its body holds the findings plus, when the research
is tied to specific files rather than a general fact, a `covers` list embedded
directly in the body:

    covers:
      - path: <file path>
        hash: <git hash-object output, or sha256:<digest> for untracked files>
      - path: <file path>
        hash: <...>

A topic with no `covers` list (a general fact not tied to specific files — how a
library behaves, an API contract) has no hash to check and is simply trusted until
manually revised, same as [Shared Lessons Store](plans-and-state.md#shared-lessons-store).

**Before any research** — inline, forked, or delegated to a worker — `todo_list`
(filter `label=research`, `search=<keywords>`) for a matching topic first. If one
exists with a `covers` list (`todo_show` for the full body):

1. Re-hash each listed file (`git hash-object <path>` for tracked files; `sha256sum`
   for untracked ones — cheap, exact, no need to read full file content to compute).
2. All hashes match → reuse the cached findings directly, cite the issue (by number),
   skip new research entirely.
3. A few files changed → delegate a narrow re-verify scoped only to the diff of
   those files (cheap — this is not a full re-research), then `todo_revise` the
   affected sections and hashes in the issue body.
4. Most or all files changed, or the topic's actual scope has clearly shifted →
   treat the issue as stale, do full research, `todo_revise` it wholesale.

**After any research** — whether it hit the cache or ran fresh — `todo_create` (new
topic) or `todo_revise` (existing one) with the `research` label. This is what makes
the cache actually pay off on the next plan; skipping the write-back defeats the
point.

## Shared Lessons Store

Durable, **non-code-specific** knowledge — gotchas, edge cases, fine-print behavior,
platform/OS quirks, logic or math traps, tips and snippets — live as `lesson`-labeled
issues in Dibs, same placement convention as [Shared Research Cache](plans-and-state.md#shared-research-cache)
(Personal Projects → "AI workflows" Group for cross-cutting tooling lessons, or the
relevant project's own Group for something project-specific). These things don't go
stale when a codebase's files change, only when the underlying tool, platform, or
understanding changes — the key distinction from research: research is versioned
against file hashes because code changes invalidate it; lessons aren't, because
they're not about a codebase's current state, they're about how something outside it
actually behaves. No `covers`/hash list needed on a lesson issue for this reason.

**Before** research or implementation touching something that smells like a gotcha
domain (an unfamiliar library, OS-specific behavior, a math/logic edge case, a
platform quirk) — `todo_list` (filter `label=lesson`, `search=<keywords>`) for a
matching topic. **After** discovering something durable and non-code-specific worth
keeping — `todo_create`/`todo_revise` it with the `lesson` label.

Being centrally in Dibs rather than per-project `.ai/lessons/` means a lesson found
while working on one project is already visible the next time any project hits the
same gotcha — no separate "is this general enough to promote" judgment call needed
the way `CLAUDE.md`'s memory-scope-discipline rule requires for personal workflow
preferences; a Dibs lesson is cross-project by construction.

## Sizing a request and the running draft

Size the request first and say the size in one line. *Small* (a few turns, one area, at most a
couple of questions): do it in the current session, no Dibs plan, no draft. *Medium* (several
steps or files, some decisions, fits one sitting): Sonnet is enough; one batched question round
and a short draft kept in the conversation or `TodoWrite`; Dibs only if it must outlive the
session. *Large* (multi-phase, audit, architecture, interacting constraints, or spans sittings): a
Dibs plan with a running draft, finalized on Opus in a fresh session. When unsure between two
sizes, take the smaller, say so, and escalate if it grows.

Model by phase: Opus for planning, architecture, audit design and subtle debugging; Sonnet for
discussion, execution and diff review; Haiku only for read/search-only workers. Planning ends when
the plan is written down and a hand-off offered; execution runs in a fresh Sonnet session or in
workers, not in the Opus planning session. At the start of a session, if the task suits the other
model, recommend the switch in one line before working.

For medium and large work keep one running draft (the plan issue's body via `todo_revise`, or a
review file if no Dibs item exists yet) and update it every turn: objective and intent in Andres's
own words, decisions made, open questions, his preferences and style for this work, constraints,
steps. The chat holds the discussion, the draft holds the state, so finalizing reads only the draft
and starts a fresh Opus session from it. Create a `plan`-labelled issue automatically once work is
explicitly multi-phase or an audit expected to span sessions; when resuming cold, look for an
in-progress plan on the objective (`todo_list` / `todo_context`, `label=plan`) and ask which to
resume. Check `sessioneer --usage` before long work; near 90% of the session or weekly quota, park
the work: file the handoff task (skill `session-handoff`), record the exact state in the plan and
release claims.

## Planning

Before delegating any implementation:

1. `todo_list`/`todo_context` for an existing, unfinished plan on this objective
   before creating a new one (see [Project State](plans-and-state.md#project-state)). If starting
   fresh, `todo_scaffold_plan` it under the right area/Group — a bare plan issue
   with no children yet is a fine stub. This gives research somewhere durable to
   land even before a full plan exists.
2. Check [Shared Research Cache](plans-and-state.md#shared-research-cache) and
   [Shared Lessons Store](plans-and-state.md#shared-lessons-store) for anything already known about
   this objective before investigating from scratch.
3. Inspect the repository and relevant environment.
4. Identify what's actually unknown — specific questions, not "investigate
   everything." Anything that needs reading multiple files/sources or several
   exploratory commands is a candidate for delegating the gathering to a research
   worker rather than doing it inline (see [Research Delegation](plans-and-state.md#research-delegation)).
5. Identify important constraints and unknowns; document uncertainties rather than
   treating assumptions as facts.
6. Create a concrete implementation plan.
7. Define acceptance criteria.
8. Identify dependencies between tasks.
9. Only then begin delegating implementation — if the work has crossed the
   delegation threshold at all (see [When This Applies](plans-and-state.md#when-this-applies)).

Prefer evidence from the actual environment over memory or generic documentation. The
plan must be detailed enough that a worker can execute a bounded step without the
orchestrator's full conversation history — because it won't have it.

## Research Delegation

The orchestrator decides *what* needs answering — that's planning judgment and stays
its job. Delegate the *gathering* when it's substantial: reading several files,
grepping broadly, running multiple exploratory commands, checking an external
API/format. Don't delegate a single quick lookup — a worker launch has fixed
overhead that a one-file read doesn't, and for a trivial question the round trip
costs more than it saves. Always check
[Shared Research Cache](plans-and-state.md#shared-research-cache) first regardless of how the
gathering will happen — a cache hit skips the delegation question entirely.

Group related questions into one research worker; split genuinely independent
questions into parallel workers (same reasoning as
[Parallel vs Sequential Workers](launching-workers.md#parallel-vs-sequential-workers)). Use the same
cheap-model-by-default tiering as implementation workers — bump up only when the
question itself needs judgment to answer correctly, not brute-force lookup volume.

**Prefer a fork over a fresh agent when the research needs context you already
have.** A fork inherits the orchestrator's full context and shares its prompt
cache — no cold-start re-derivation — but it always runs on the orchestrator's own
model; there is no cheaper-model option for a fork (see
[Model Tiering](model-routing.md#model-tiering)). A fresh subagent or cross-tool worker starts cold
and has to re-derive that context itself, but can run on a genuinely cheaper model.
Pick based on which cost actually dominates for this question — context
re-derivation, or per-token price — not by default.

Research workers are lighter-weight than implementation workers: there's no task
issue yet at this point, so they don't need a task ID or the full worker protocol —
just the question, read-only, plus the instruction to check and update the shared
research/lessons knowledge records in Dibs. Cross-tool research workers still get
the [worker session tag](launching-workers.md#worker-session-tagging) prepended as their literal first
line (use `research` in place of a real task id, since there isn't one yet);
in-process ones skip it.

```
You are a RESEARCH WORKER in the orchestrator/worker protocol
(skill: orchestrator-worker, or read
~/dotfiles/ai/skills/orchestrator-worker/SKILL.md if not auto-loaded).

Project: <absolute path>
Plan: Dibs issue #<plan issue id> (dibs MCP server, or the todo:agent:* CLI if MCP
isn't reachable from this tool — see Project State)
Research question(s): <specific and bounded — not "investigate the codebase">

First todo_list (label=research, then label=lesson; search=<keywords>) for anything
already known about this — reuse or narrowly re-verify per Shared Research Cache
rather than starting from scratch if a matching topic exists.

Investigate read-only — do not modify anything. Report back concisely: what you
found, where (file paths/line numbers, commands run), and flag anything you
couldn't confirm rather than guessing. State which agent/subagent type and model
you ran as. Write durable findings as a research-labeled Dibs issue (with a covers
list of file paths/hashes) and any non-code-specific gotcha as a lesson-labeled one
(todo_create, or todo_revise if updating an existing topic). If it's also worth
keeping in this plan's own record, todo_comment it on the plan issue too. If the
Dibs tooling itself misbehaves along the way, todo_report_bug it rather than working
around it silently.
```

**Trust, but verify what matters.** Treat a research worker's findings as reliable
for minor/local facts. For anything the plan critically depends on — a claim that,
if wrong, would derail multiple downstream tasks — spot-check it yourself before
committing to the plan. A wrong implementation usually fails a test; a wrong research
finding just quietly becomes a wrong plan, so it doesn't get the same automatic
safety net. The same caution applies to a cache hit from a `research`-labeled Dibs
issue that a critical decision rests on — a matching hash means the file hasn't
changed, not that the original finding was correct.

## Task Decomposition

Tasks should be independently understandable, reasonably bounded, testable, and small
enough that a worker completes them without losing context.

Avoid both extremes:

- **Too large**: "Build the entire feature."
- **Too small**: "Rename this variable."

Aim for units like: "Investigate and document the input data format," "Implement the
parser for format X," "Add validation for case Y," "Add tests for malformed input."
