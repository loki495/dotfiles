---
name: orchestrator-worker
description: Default protocol for any multi-step coding work — solo, forked, or delegated to workers. A plan is a `plan`-labeled issue in Dibs (the personal MCP-backed task tracker, registered as the `dibs` MCP server; CLI fallback via `docker compose -f /home/andres/www/dibs/docker-compose.yml exec` when a tool can't reach MCP directly), created automatically once work is explicitly multi-phase or spans sessions, so a fresh session (this one resuming later, or a different tool entirely) can pick it up cold from Dibs alone — no local plan files. Small work escalates to full delegation (workers, model tiering, parallel execution) automatically when it's clearly warranted, or with a quick check when it's ambiguous — never silently. Two shared, cross-plan knowledge stores back every plan, also in Dibs: `research`-labeled issues (checksum-versioned against the files they're based on) and `lesson`-labeled issues (durable non-code gotchas — platform quirks, library fine print, logic traps) — checked before and updated after any research or implementation step, filed under Personal Projects → AI workflows unless project-specific. Tool-agnostic throughout: Claude Code, opencode, Codex, and agy can each play orchestrator or worker — via the `dibs` MCP server where registered, the `todo:agent:*` CLI otherwise. Use this by default for multi-step work, not only when explicitly asked.
---

# Orchestrator/Worker Protocol

Tool-agnostic. Any of Claude Code, opencode, Codex, or Antigravity's `agy` can play
either role — orchestrator in one project, worker in another, sometimes both in the
same run (see [Launching Workers](#launching-workers)). Nothing here assumes a
specific tool; where mechanics differ per tool, that's called out explicitly.

This is the **default** way multi-step work happens on this machine — not a protocol
to invoke on request. See [When This Applies](#when-this-applies) for exactly what
triggers a plan folder and what triggers full delegation.

## Core principle

    investigate
        |
      plan
        |
    delegate?  <--- see When This Applies: light work stays here, done directly or forked
        |
     worker  <--- cheapest capable model, any tool, one bounded task
        |
   +----+----+
   |         |
complete   blocked
   |         |
   |      question
   |         v
   |    orchestrator  <--- stays on whatever model it was launched with
   |         |
   |    answer / re-plan
   |         v
   |       worker (same or next task; independent tasks may run in parallel)
   |         |
   +----+----+
        v
      review
        v
     verify
        v
     complete

The orchestrator optimizes for correctness and useful delegation, not for minimizing
the number of worker launches. A worker is allowed to stop and ask. The orchestrator
is expected to listen.

---

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
[Model Tiering](#model-tiering), consider parallel execution) once a plan is
underway, when:

- the work is expected to need a large tool-call/context footprint (many files, a
  test suite run, broad exploration) — see the growth-cost argument in
  [Model Tiering](#model-tiering);
- there are genuinely independent subtasks that could run in parallel;
- a cheaper model is plausibly capable of a bounded piece of the work and the cost
  difference is worth the coordination.

This should happen **automatically when it's clearly warranted, or with one quick
check-in when it's ambiguous** — never silently. If a plan turns out to need
delegation partway through, that's normal; nothing about the plan issue changes,
only how heavily its comments/claims get used (see [Project State](#project-state) —
every plan is a real Dibs issue from creation, light or not).

A plan that never needs delegation is not a failure of the protocol — most solo
work, once it clears the "create a plan" bar, stays solo the whole way through.

---

## Role: Orchestrator

The orchestrator is the senior agent responsible for:

- understanding the overall objective;
- investigating the environment and repository;
- creating and maintaining the implementation plan;
- decomposing work into bounded tasks when delegating;
- delegating implementation to workers once escalated (see
  [When This Applies](#when-this-applies));
- reviewing worker results;
- resolving worker questions and blockers;
- deciding when additional worker iterations are required;
- performing final validation and review;
- telling the user, **before every worker launch** (not just when asked), which
  agent/tool and model it's about to use and why — see
  [Worker Launch Reporting](#worker-launch-reporting).

For work that hasn't crossed the delegation threshold, the orchestrator does the
work directly rather than manufacturing a worker launch for its own sake — see
[When This Applies](#when-this-applies) and the "don't delegate a single quick
lookup" floor in [Research Delegation](#research-delegation). Once delegation is
warranted, the orchestrator should generally avoid implementing application code
itself — its job shifts to directing, reviewing, and making architectural
decisions. See [Model Tiering](#model-tiering) for why this split exists, not just
as a division of labor.

## Role: Worker

A worker is an implementation agent responsible for:

1. Reading this protocol (see [Worker Context](#worker-context)).
2. Reading the current plan and state.
3. Identifying its assigned task.
4. Checking [Shared Research Cache](#shared-research-cache) and
   [Shared Lessons Store](#shared-lessons-store) for anything already known before
   investigating from scratch.
5. Inspecting relevant code/data itself — not just trusting the orchestrator's
   description of it.
6. Implementing the task.
7. Running appropriate tests/checks.
8. Updating task status.
9. Recording relevant results — as a `todo_comment` checkpoint on its task issue, and
   in the shared research/lessons knowledge records when applicable (see
   [Worker Completion Protocol](#worker-completion-protocol)).
10. Reporting completion or blockers, and self-reporting via `todo_report_bug` if the
    Dibs tooling itself misbehaves along the way (distinct from a plan question —
    see [Worker Questions and Blockers](#worker-questions-and-blockers)).

The worker should not redesign the project without consulting the orchestrator. It
may make reasonable local implementation decisions consistent with the plan; major
architectural decisions belong to the orchestrator.

---

## Project Isolation

All project work happens inside the designated project directory. Do not create or
modify files outside it. External data may be read when the project needs it, but
treat it as read-only unless the project explicitly requires otherwise. Never modify
unrelated files, repositories, configuration, credentials, or user data.

---

## Project State

A project's multi-step work lives in **Dibs** — the personal MCP-backed task
tracker (`/home/andres/www/dibs`) — instead of local plan files. Reach it through
the `dibs` MCP server (registered at user scope for Claude Code as of 2026-09-13;
register it the same way in any other tool's own MCP config before relying on it
there — `claude mcp list`/that tool's equivalent shows whether it's connected) or,
when a tool can't reach MCP directly, the `todo:agent:*` CLI fallback:
`docker compose -f /home/andres/www/dibs/docker-compose.yml exec -T -u www-data app
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
(current step, worker model/mechanism/cost — see [Cost Reporting](#cost-reporting) —
architectural decisions, known limitations, outstanding blockers), or on the
**specific task issue** for anything task-scoped (a blocker, a result, a
verification outcome — see [Worker Questions and Blockers](#worker-questions-and-blockers)).
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

---

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
manually revised, same as [Shared Lessons Store](#shared-lessons-store).

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

---

## Shared Lessons Store

Durable, **non-code-specific** knowledge — gotchas, edge cases, fine-print behavior,
platform/OS quirks, logic or math traps, tips and snippets — live as `lesson`-labeled
issues in Dibs, same placement convention as [Shared Research Cache](#shared-research-cache)
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

---

## Planning

Before delegating any implementation:

1. `todo_list`/`todo_context` for an existing, unfinished plan on this objective
   before creating a new one (see [Project State](#project-state)). If starting
   fresh, `todo_scaffold_plan` it under the right area/Group — a bare plan issue
   with no children yet is a fine stub. This gives research somewhere durable to
   land even before a full plan exists.
2. Check [Shared Research Cache](#shared-research-cache) and
   [Shared Lessons Store](#shared-lessons-store) for anything already known about
   this objective before investigating from scratch.
3. Inspect the repository and relevant environment.
4. Identify what's actually unknown — specific questions, not "investigate
   everything." Anything that needs reading multiple files/sources or several
   exploratory commands is a candidate for delegating the gathering to a research
   worker rather than doing it inline (see [Research Delegation](#research-delegation)).
5. Identify important constraints and unknowns; document uncertainties rather than
   treating assumptions as facts.
6. Create a concrete implementation plan.
7. Define acceptance criteria.
8. Identify dependencies between tasks.
9. Only then begin delegating implementation — if the work has crossed the
   delegation threshold at all (see [When This Applies](#when-this-applies)).

Prefer evidence from the actual environment over memory or generic documentation. The
plan must be detailed enough that a worker can execute a bounded step without the
orchestrator's full conversation history — because it won't have it.

---

## Research Delegation

The orchestrator decides *what* needs answering — that's planning judgment and stays
its job. Delegate the *gathering* when it's substantial: reading several files,
grepping broadly, running multiple exploratory commands, checking an external
API/format. Don't delegate a single quick lookup — a worker launch has fixed
overhead that a one-file read doesn't, and for a trivial question the round trip
costs more than it saves. Always check
[Shared Research Cache](#shared-research-cache) first regardless of how the
gathering will happen — a cache hit skips the delegation question entirely.

Group related questions into one research worker; split genuinely independent
questions into parallel workers (same reasoning as
[Parallel vs Sequential Workers](#parallel-vs-sequential-workers)). Use the same
cheap-model-by-default tiering as implementation workers — bump up only when the
question itself needs judgment to answer correctly, not brute-force lookup volume.

**Prefer a fork over a fresh agent when the research needs context you already
have.** A fork inherits the orchestrator's full context and shares its prompt
cache — no cold-start re-derivation — but it always runs on the orchestrator's own
model; there is no cheaper-model option for a fork (see
[Model Tiering](#model-tiering)). A fresh subagent or cross-tool worker starts cold
and has to re-derive that context itself, but can run on a genuinely cheaper model.
Pick based on which cost actually dominates for this question — context
re-derivation, or per-token price — not by default.

Research workers are lighter-weight than implementation workers: there's no task
issue yet at this point, so they don't need a task ID or the full worker protocol —
just the question, read-only, plus the instruction to check and update the shared
research/lessons knowledge records in Dibs. Cross-tool research workers still get
the [worker session tag](#worker-session-tagging) prepended as their literal first
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

---

## Task Decomposition

Tasks should be independently understandable, reasonably bounded, testable, and small
enough that a worker completes them without losing context.

Avoid both extremes:

- **Too large**: "Build the entire feature."
- **Too small**: "Rename this variable."

Aim for units like: "Investigate and document the input data format," "Implement the
parser for format X," "Add validation for case Y," "Add tests for malformed input."

---

## Worker Context

Every worker must be instructed, at minimum, to read:

- this protocol (the `orchestrator-worker` skill if the worker's tool auto-loads
  shared skills; otherwise point it explicitly at
  `~/dotfiles/ai/skills/orchestrator-worker/SKILL.md`);
- this plan's issue and its own task issue in Dibs (`todo_show` on each, per
  [Project State](#project-state)) — via the `dibs` MCP server if this worker's tool
  has it registered, the `todo:agent:*` CLI otherwise;
- `todo_list` (label=research, then label=lesson) for anything already known
  relevant to its task.

The worker inspects the repository itself rather than relying entirely on the
orchestrator's description, and must not assume the plan is correct if repository
evidence contradicts it — when it finds a contradiction, it stops and asks (see
below).

### Worker prompt template

Use this as the starting point for every worker launch, filled in per task. If this
is a **cross-tool** launch (codex/opencode/agy), prepend the
[worker session tag](#worker-session-tagging) as the literal first line, before
`You are a WORKER...`. Skip the tag for in-process launches (Claude Code's `Agent`
tool) — those never become a separately-visible session, so there's nothing to tag.

```
You are a WORKER in the orchestrator/worker protocol
(skill: orchestrator-worker, or read
~/dotfiles/ai/skills/orchestrator-worker/SKILL.md if not auto-loaded).

Project: <absolute path>
Plan: Dibs issue #<plan issue id> (dibs MCP server, or the todo:agent:* CLI if MCP
isn't reachable from this tool)
Your task: Dibs issue #<task issue id>

Before doing anything:
1. todo_show the plan issue and your own task issue.
2. todo_list (label=research, then label=lesson) for anything already known
   relevant to this task.
3. todo_claim your task issue (capability token comes back once — hold onto it for
   todo_heartbeat/todo_release/todo_complete).
4. Confirm your assigned task and its acceptance criteria.
5. Inspect the actual code/data yourself.

Then implement the task and follow the Worker Completion Protocol, or the Worker
Questions and Blockers protocol if you hit something you must not guess on — and
todo_report_bug anything that's actually broken in the Dibs tooling itself, as
distinct from a plan question. Include which agent/subagent type and model you ran
as, and your cost per Cost Reporting, in your report.
```

---

## Worker Completion Protocol

When a worker successfully completes a task:

1. Verify the acceptance criteria are actually satisfied.
2. Run appropriate tests/checks.
3. `todo_complete` the task issue (optionally with a `summary` — posts as a result
   comment and releases the claim in the same call).
4. `todo_comment` the plan issue if relevant to the overall state (the orchestrator
   should confirm/finalize this on review, not treat the worker's own comment as
   final).
5. If the task produced a reusable investigative finding (code-specific or general),
   `todo_create`/`todo_revise` it in [Shared Research Cache](#shared-research-cache).
   If it surfaced a durable non-code-specific gotcha, do the same in
   [Shared Lessons Store](#shared-lessons-store).
6. Return a concise completion report covering: what changed, what was tested, any
   assumptions made, any remaining concerns, and which agent/subagent type and model
   it actually ran as (confirms what was used, in case of a fallback from what the
   orchestrator requested).
7. Report cost — see [Cost Reporting](#cost-reporting) for what's actually available
   to report and how to report it honestly.

This applies equally whether the step was done by a delegated worker or by the
orchestrator working directly on a light plan — whoever did the step closes/comments
the task, updates the plan issue, and updates the shared knowledge records, not just
workers.

A worker's `OK` is not sufficient evidence the task is correct — the orchestrator
independently reviews every result (see [Code Review](#code-review)).

### Cost Reporting

What a worker can honestly report about its own cost depends entirely on how it ran.
Don't ask for a number a worker structurally cannot know, and don't let an estimate
pass as an exact figure:

- **Cross-tool CLI workers with a JSON/machine-readable output mode** — confirmed for
  codex: `codex exec --json` emits a `turn.completed` event carrying a real `usage`
  object (`input_tokens`, `cached_input_tokens`, `cache_write_input_tokens`,
  `output_tokens`); check each tool's own `--help`/docs for its equivalent rather than
  assuming the flag name or field names carry over. Capture that event and report the
  real numbers, plus a rough dollar estimate if the model's per-token pricing is
  known. This is exact, not a guess — use `--json` (or equivalent) by default for
  cross-tool worker launches so this is available.
- **In-process Claude Code subagents cannot self-report exact token usage.** A
  subagent has no tool that exposes its own token count from inside its own
  generation — that accounting only exists afterward, in its own persisted session
  transcript on disk (under `~/.claude/projects/<project>/**/*.jsonl`; the exact
  layout can shift between Claude Code versions, so locate the right file by
  recency/session-id rather than hardcoding a path). If genuinely precise numbers are
  needed, the *orchestrator* can read that file after the worker completes — that's
  how a real token-usage audit of this protocol was actually done. This is a
  deliberate deep-dive, not a routine step for every task; don't add it as overhead
  to normal delegation.
- **When exact numbers aren't available** (the common case for in-process workers),
  report proxy signals instead: number of tool calls made, roughly how many files
  were read/written, and task duration if known. Label these explicitly as
  estimates, not token counts — a vague impression framed as if it were a hard number
  is worse than an honest "exact usage not visible for this run."
- **Cross-tool workers launched without a JSON/verbose mode have genuinely
  unrecoverable cost** — the orchestrator never sees their token usage, and their
  real cost (a separate provider's billing) isn't visible from here at all. State
  this plainly in a `todo_comment` rather than omitting a cost line silently; a
  known gap is more useful than a missing one.

Record whatever was actually captured — exact or proxy — in a `todo_comment` on the
plan issue alongside the model/mechanism/justification already required there, so a
long session accumulates a readable cost trail instead of requiring a transcript dig
to reconstruct later.

---

## Worker Questions and Blockers

Workers must **not** guess when they encounter:

- ambiguous or contradictory requirements;
- unexpected data formats;
- missing information;
- architectural conflicts;
- potentially destructive behavior;
- security concerns;
- uncertainty that could materially affect correctness.

Instead:

1. `todo_comment` the task issue with the question: what was discovered, why the
   plan can't safely continue, exactly what decision/information is needed, options
   if useful, a recommendation if there is one. Leave the task issue open (don't
   `todo_complete` it) — an unclaimed or released task with an unanswered question
   comment on it *is* the "blocked" state; there's no separate status field to set.
2. `todo_release` the claim if one is held, so the task isn't left claimed while
   waiting on a decision nobody's actively working toward.
3. Leave the working tree in a coherent state.
4. Stop and return control to the orchestrator.

This is distinct from `todo_report_bug` — a question needs a **human/orchestrator
decision** about the plan; `todo_report_bug` is for when the Dibs tooling itself is
broken or confusing, independent of any plan decision.

## Blocker Resolution Loop

1. The orchestrator reads the question (`todo_show` the task issue's comments),
   investigates if necessary, and makes the decision.
2. `todo_comment`s the answer onto the same task issue.
3. `todo_revise`s the plan issue's body if the plan changes.
4. Launches a worker again (fresh — it has no memory of the earlier attempt beyond
   what's in Dibs), telling it to `todo_claim` and continue from the blocked task.

Do not restart the whole project over one blocker. A task cycling through
`worker -> blocked -> orchestrator decision -> worker -> done` is normal, not a
failure — a worker surfacing something the orchestrator missed is the protocol
working as intended.

---

## Model Tiering

The orchestrator and the worker do fundamentally different work and should normally
run different-cost models — this is the point of the split, not an incidental detail:

- **Orchestrator**: plans, decomposes, resolves ambiguity, reviews correctness. Stay
  on whatever model the orchestrating session was already launched with — don't
  switch up to the strongest/most expensive model available "just because" the
  session is now acting as an orchestrator. The split isn't "orchestrator must be
  the priciest model"; it's "workers should be cheaper than the orchestrator."
- **Worker**: executes one already-decomposed, bounded task. Use the **cheapest
  model, in any available tool, that's capable of doing it satisfactorily** — not
  just the orchestrating tool's own cheap tier. Workers run more often, and
  sometimes in parallel, so their per-token cost is what actually compounds; this is
  where token spend is controlled, and it's controlled better by actually comparing
  options than by defaulting to whatever's already open. See
  [In-Process vs Cross-Tool](#in-process-vs-cross-tool) for how to compare across
  tools without making the comparison itself expensive.

**A fork is not a lever for model cost.** A fork always runs on the orchestrating
session's own model — a `model` override passed to a fork is ignored. Forking saves
tokens a different way: it inherits full context and shares the prompt cache, so
there's no cold-start re-derivation the way a fresh agent has. Choose between a fork
and a fresh/cross-tool worker based on which cost actually dominates for the task at
hand — context re-derivation (fork wins) or per-token price (a cheaper fresh
worker wins) — not out of habit. See also
[Research Delegation](#research-delegation) for this same tradeoff applied to
research specifically.

Model tier isn't the only source of savings, and for tool-call-heavy tasks it usually
isn't the dominant one. A worker that makes many tool calls builds a large context
over the course of its own run; doing that exploration in a disposable worker means
the growth gets discarded when the worker finishes, instead of becoming permanent,
repeatedly-re-read context in a long-running orchestrator session — a real audit found
one delegated task whose worker context grew past 400k tokens over ~80 tool calls, and
containing that inside a worker rather than the orchestrator was worth far more than
the model-tier difference alone, since an orchestrator's accumulated context gets
re-read on every subsequent turn for the rest of the session. A task expected to need
many tool calls or a large exploration footprint is worth delegating for this reason
by itself, even before comparing model prices — this is also why it's part of the
[escalation criteria](#when-this-applies) above.

Bump a worker to a stronger model only when the bounded task itself genuinely
requires deep reasoning (diagnosing a subtle bug, reconciling conflicting
constraints) — not by default "to be safe," and not just because it's the model
already running. Whichever model gets picked, state *why* — "cheapest capable option
available" is a real justification, but it has to have actually been checked against
the alternatives, not assumed. Record the exact worker model, which tool it ran in,
and that justification as a `todo_comment` on the plan issue. Don't assume a model's cost or availability
from its name; verify with the tool's own model listing before launching
(`opencode models`, `codex debug` / `-c model=...` docs, `agy models`, etc.).

The orchestration protocol itself must not depend on a particular model's identity —
the same project should be able to swap worker models later (a free tier, a stronger
coding model, a different provider) without changing anything else.

---

## Launching Workers

**General principle**: launch the worker as an isolated, non-interactive invocation
scoped to the project directory, with its own explicit model, and a prompt built from
the [worker prompt template](#worker-prompt-template) above. Prefer this over
simulating the worker inline in the orchestrator's own context — the point is to keep
the expensive orchestrator context free of grunt-work tool output, and to run the
worker on a cheaper model.

Three of the four tools converge on the same shape — a headless CLI subprocess that
blocks until done and returns its output:

| Tool | Headless invocation | Model flag | Notes |
|---|---|---|---|
| opencode | `opencode run --model <provider/model> --title "<tag>" "<worker prompt>"` | `--model` | Foreground subprocess; cwd = project dir. `--title` is a real, confirmed flag — always set it to the [worker session tag](#worker-session-tagging) rather than leaving it to the default truncated-prompt title. Verify exact syntax with `opencode run --help` / `opencode models` — do not invent provider/model names. |
| Codex | `codex exec -m <model> --json "<worker prompt>" < /dev/null` (alias `codex e`) | `-m`/`--model` | Foreground subprocess. **Always redirect stdin from `/dev/null`** — confirmed 2026-08-30: `codex exec` can hang indefinitely waiting on stdin even when a prompt is given as an argument, if stdin isn't a TTY and isn't explicitly closed. `--json` captures real usage, see [Cost Reporting](#cost-reporting). No title/name flag exists — see [Worker Session Tagging](#worker-session-tagging) for how tagging works without one. See [Background Launch Verification](#background-launch-verification) before ever backgrounding a codex (or any cross-tool) worker without waiting on it — `codex agents` needs a real TTY and cannot be used from a script. |
| agy (Antigravity) | `agy -p --agent <name> --model <model> "<worker prompt>"` | `--model` | Foreground subprocess (`-p`/`--print` = non-interactive). No title/name flag exists either — see [Worker Session Tagging](#worker-session-tagging). `--effort` isn't supported on every model. agy has account-wide usage quotas — check headroom before launching several workers in a row. |

Claude Code is the one exception, since the orchestrator is usually already running
inside it: use the `Agent` tool directly rather than shelling out to `claude -p`.
Pick a `subagent_type` (a purpose-built agent, or `general-purpose`), pass the worker
prompt as `prompt`, and use the `model` parameter to pin the cheaper tier — this
override works for a real subagent launch but is silently ignored for
`subagent_type: "fork"` (see [Model Tiering](#model-tiering)). Runs synchronously by
default (the report comes back in the tool result); use `subagent_type: "fork"` with
background execution when launching workers in parallel (see below) so their tool
output doesn't fill the orchestrator's own context.

Confirmed as of 2026-08-29 against the installed versions on this machine — CLI flags
drift between releases, so re-verify with the tool's own `--help` if it's been a
while.

### Worker Session Tagging

A cross-tool worker (codex/opencode/agy) becomes its own real session in whatever
that tool tracks — and, on this machine, gets auto-adopted into
claude-session-manager's dashboard alongside every session a human started directly.
Without a way to tell them apart, a worker launched for a 30-second bounded task looks
identical to a session someone's actively driving. Tag every cross-tool worker so it
can be identified and, by default, hidden:

**Put this as the literal first line of every worker's prompt** (before the actual
task text), regardless of tool:

    [WORKER session=<plan-issue-id>/<task-issue-id> parent=<parent-session-id>]

- `<plan-issue-id>`/`<task-issue-id>` — the plan and task issue numbers in Dibs, per
  [Project State](#project-state).
- `<parent-session-id>` — the orchestrator's own session identity, if it's knowable.
  On this machine, an orchestrator running inside a claude-session-manager-spawned
  tmux pane already has this in its own environment as `$CSM_SESSION_NAME`
  (confirmed: `SessionLifecycleService::create_cc_session()`/`resume_cc_session()` set
  it at spawn time, `host-agent/lib/Services/SessionLifecycleService.php:97,258`) —
  read it directly, don't invent a new mechanism. Use `unknown` if it's unset or the
  orchestrator isn't running under something that tracks session identity — don't
  guess or fabricate one.

Where a tool has a real, explicit title-setting flag, **also** pass this exact string
as the title (confirmed for opencode's `--title`, per the table above) — that's a
reliable, structured signal on top of the prompt-embedded one. Where no such flag
exists (confirmed for codex and agy, as of 2026-08-30), the prompt-embedded line is
the only mechanism available; whether it reliably survives into whatever
name/preview text each tool ends up recording is **not independently verified** —
codex's own raw session record stores no literal name/preview field at all (that
text appears to be computed dynamically when a thread list is requested, not stored),
so confirm this against a real listing once anything is built to detect the tag,
rather than assuming it works.

### Background Launch Verification

A real orchestration run hit a genuine race: two `codex exec` workers were launched,
the launching harness reported both complete, but both were still writing output
minutes later — a concurrent write corrupted `PLAN.md`'s status section (the plan was
still file-based at the time) until the stray processes were killed and the files
manually reconciled. Investigated in two passes: a live test of a single,
properly-waited `codex exec` call (2026-08-30), then later a direct read of the
actual incident transcript (2026-08-30), which found the exact cause. That specific
corruption vector — two writers racing on the same shared file — is now structurally
impossible: each task is its own Dibs issue, and `todo_claim`'s hardened,
capability-token-bound claim already prevents two workers from touching the same
task concurrently. The underlying lesson still applies fully, though: **a background
launch reporting "done" is not the same as the worker actually being done**,
regardless of what the worker is racing over.

**Confirmed root cause**: the real launch used
`nohup codex exec ... & ; echo "PID: $!"` — backgrounded with no `wait` and no poll.
The wrapping shell command returns almost immediately once the process is
backgrounded, so "the harness reported completed" was true of the *wrapper*, not the
worker — the notification was accurate about the thing it was actually watching, just
not the thing that mattered. This is a general shell-launch anti-pattern, not
something specific to codex: any cross-tool worker launched with bare backgrounding
(`&`, `nohup ... &`, `disown`) and no `wait`/poll afterward has the same failure mode.
Never do this — either run the worker in the foreground and block on it (the default
for all three cross-tool CLIs, per the table above), or, if backgrounding is genuinely
needed for parallelism, capture the PID and `wait` on it or poll for a completion
sentinel (below) — never just log the PID and move on.

Secondary, codex-specific factor: codex's actual work runs through a shared local
`app-server` daemon plus `codex-code-mode-host` processes that persist independently
of any single `codex exec` invocation (`codex app-server daemon ...`, always-on
regardless of whether a worker is active). A single, properly-waited `codex exec` call
completed cleanly against this daemon in direct testing, so the daemon by itself
wasn't the failure here — but it's a plausible reason codex specifically could still
leave orphaned work behind even with a correctly-`wait`ed launch, worth keeping in
mind if a future incident doesn't match the missing-`wait` pattern above.

Also corrected: `codex agents` — this skill previously pointed here to check on a
running session — **requires an interactive TTY** (`ERROR: stdin is not a terminal`
when run from a script or pipe). It cannot be used by an orchestrator. No scriptable
"is this thread actually idle" query exists in the codex CLI (checked `codex debug`,
`codex exec resume`, `codex app-server daemon version` — none fit); this is exactly
why the sentinel approach below matters, rather than looking for a status-check
command.

Regardless of root cause, verification still shouldn't rest on a single "done" signal
for any cross-tool worker running in the background:

1. **Foreground + wait is the default.** Only background a cross-tool worker when the
   task genuinely needs parallelism (see [Parallel vs Sequential Workers](#parallel-vs-sequential-workers),
   which already defaults to sequential). codex specifically had a confirmed
   concurrent-write race, so treat sequential as firmer still for codex until it's
   been re-tested clean under real parallel load.
2. **Require a real completion sentinel, not just a process-exit signal**, whenever a
   worker does run in the background. `todo_complete` on the task issue *is* the
   sentinel — it's a single durable, structured signal (the issue closes, the claim
   releases) rather than an artificial marker string, and it's exactly the worker's
   own last action per [Worker Completion Protocol](#worker-completion-protocol).
   The orchestrator treats the worker as finished only once `todo_claim_status` (or
   `todo_show`) actually confirms the task closed and the claim released — not
   merely because the launching call returned or a background-task notification
   fired. Called out explicitly here because this exact gap has already caused real
   corruption once, under the old file-based sentinel.
3. **Poll for the sentinel** (a short loop calling `todo_claim_status`/`todo_show` on
   the task issue) rather than relying on a single "done" event — see the Monitor
   tool's guidance on polling loops if launching from Claude Code.
4. **If a stray process is still visible after the sentinel appears**, don't assume
   it's hung — disk writes can trail the sentinel by a few seconds. Recheck after a
   short pause before concluding it's actually stuck. Only kill a process that's
   clearly well past the task's expected size, and always re-read (don't assume) any
   of its plan's files it touched afterward, the same way the original incident was
   recovered from.
5. **Give each parallel cross-tool worker its own project directory** (`-C <dir>` or
   equivalent, per [Project Isolation](#project-isolation)) — this narrows, though
   doesn't by itself eliminate, the chance of state bleeding between concurrent
   workers sharing one tool's backend.

**A distinct failure mode from all of the above**: an in-process worker (fork or
subagent) that itself starts a long-lived background process as part of its own
work — a `docker run`/`sleep infinity` container it plans to `docker exec` into
repeatedly, a dev server, anything not expected to exit on its own — must clean
that process up before finishing. If the *worker itself* gets externally
interrupted before reaching that cleanup (a rate limit, a crash, being killed),
nothing in this protocol watches for it: the "worker died" notification says
nothing about what it left running. Confirmed 2026-09-02: a fork doing Docker-
based CI testing hit a session rate limit mid-task, and the `archlinux` container
it had started (`sleep infinity`, meant to be `docker exec`'d into) kept running
for 8+ hours afterward, undetected, consuming disk. After any worker — in-process
or cross-tool — reports anything other than clean completion, check for what it
might have left running (`docker ps -a`, relevant process list) before assuming
"failed" means "nothing changed." This is a different check than the sentinel-
polling above, which only covers the launcher-side wait/race case, not a worker's
own orphaned children.

### In-Process vs Cross-Tool

Communication goes through Dibs (the `dibs` MCP server, or its `todo:agent:*` CLI
fallback), so it doesn't matter to the protocol whether a worker runs in-process
(the orchestrator's own `Agent`/subagent mechanism) or as a separate cross-tool
subprocess (`opencode run`, `codex exec`, `agy -p`) — either way the worker reads
its plan and task issues and reports back through the same claim/comment calls. The
orchestrator never needs tool-specific handling once a worker is launched; it just
watches for `todo_claim_status`/`todo_show` updates and the return value like any
other worker.

**One real prerequisite, unlike the old file-based version**: reaching Dibs at all
requires either the `dibs` MCP server registered in that specific tool's own config
(each tool has its own separate MCP registration — Claude Code's is user-scoped as
of 2026-09-13; opencode/codex/agy each need their own, done the same way, before a
worker in that tool can call `todo_*` tools directly), or falling back to the
`todo:agent:*` CLI via `docker compose -f /home/andres/www/dibs/docker-compose.yml
exec`, which works from any tool regardless of its own MCP support. Confirm which
path a given worker actually has before assuming MCP tool calls will just work —
include the CLI fallback form in its prompt either way, since a cross-tool worker
may not have MCP registered even if the orchestrator does.

**Prioritize the cheapest capable model for every worker, in-process or not** — don't
default to in-process just because it's already open. The in-process/cross-tool
question is purely mechanical (how do I reach the cheapest capable option), not a
reason to skip looking for it. Remember a fork is not part of this comparison at
all — it has no model choice, see [Model Tiering](#model-tiering).

**Keep the comparison itself cheap**, so "always look" doesn't turn into its own
research task:

1. Once per orchestration session (not once per worker), find out what's actually
   available: which tools are installed (`command_exists`), authenticated, and what
   they charge/offer — use each tool's own lightweight status command
   (`codex doctor`, agy's usage check, `opencode models`) rather than guessing.
   Re-check a specific tool mid-session only if something would plausibly have
   changed it (you've launched several workers there since and quota could be
   tight), not before every single launch.
2. For each worker, pick the cheapest model from that known set that you judge
   capable of the task. When two options are close enough in cost that the
   difference doesn't matter, prefer in-process — it's simpler, and simplicity is
   the tiebreaker, not the default.
3. Don't gamble a task on an unfamiliar cheap/free model without some basis for
   trusting it with this specific task — if it turns out inadequate, the wasted
   round trip costs more than picking the right tier up front would have. This
   matters more as task size grows; a small task failing over is cheap either way.
4. **In-process is always the fallback**, regardless of why: nothing else installed,
   nothing else authenticated, everything else out of quota, or the capability call
   is genuinely too close to guess. Don't let the search for a cheaper option block
   real work — fall back and move on.

Verification doesn't change based on where a worker ran: the orchestrator reviews a
cross-tool worker's result exactly like an in-process one (see
[Code Review](#code-review)). If a cross-tool worker's result is inadequate, that's
not a protocol failure — decide whether to re-delegate on the same tool or fall back
to in-process, the same way any blocked/incorrect task gets re-run.

Record which mechanism was actually used, alongside the model, in a `todo_comment`
on the plan issue.

### Worker Launch Reporting

Tell the user this **before launching**, not after and not only when asked — this is
what makes "prioritize the cheapest capable model" verifiable rather than a claim:

```
Launching worker — <task ID / description>
Agent/tool: <e.g. Claude Code Agent (general-purpose) | opencode | codex | agy>
Model: <model>
Why: <the actual comparison, not just a label — e.g. "cheapest available across
      installed tools capable of this bounded mechanical edit (checked opencode/
      codex/agy: X had no quota, Y not authenticated)" or "bumped up from the
      cheapest tier because this task requires diagnosing a race condition">
```

This is a report, not a request for permission — the orchestrator still has standing
authority to launch workers per [Blocker Resolution Loop](#blocker-resolution-loop)
and the rest of this protocol. It exists so a wrong or lazy model choice ("used
whatever was already running") is visible in the moment, not discovered later by
asking.

### Parallel vs Sequential Workers

Sequential is the default: one task's result often changes what the next task should
be, not because the old file-based version needed it to avoid concurrent writers —
Dibs's per-issue claims already make that concern structurally moot (see
[Task Claims](#task-claims)).

Launch workers in parallel only when:

- the tasks are genuinely independent — no shared project files, no dependency
  listed in the plan issue's body;
- each worker has a distinct, bounded slice of work with no overlapping writes;
- the orchestrator will review each result independently before marking it done.

When running parallel workers, give each its own distinct task issue and instruct it
to touch only files within its own task's scope, and to `todo_claim` only that task.
Each worker's claim, heartbeat, and comments are already scoped to its own task
issue — there's no shared status file for parallel workers to clobber the way
`PLAN.md`/`STATE.md` required careful "only touch your own line" discipline before.
Only the orchestrator revises the plan issue's body; workers each comment on their
own task issue.

---

## Token Efficiency Practices

These apply to every plan, light or fully delegated — they're what makes file-based
state actually cheaper than re-explaining things in conversation, not just
differently organized:

- **Verify via diffs/status, not full re-reads.** After an edit, don't re-read the
  whole file to confirm it worked — a tool that errors on failure already proves it
  didn't silently fail. Use `git diff`/`git status` for a summary of what actually
  changed, not `cat` of the full file.
- **Prefer targeted search over full reads.** `grep`/glob for a symbol or pattern
  before reading a whole file just to check whether something exists in it.
- **Run checks with quiet/concise output**, and keep only pass/fail + errors in
  `todo_comment` checkpoints — never paste raw verbose CI-style output (full
  test-runner logs, progress bars, full lint dumps) into one. If a tool has a
  terser mode (compact test output, a trimmed static-analysis formatter), use it;
  either way, summarize before posting a checkpoint.
- **Batch independent steps.** Tool calls whose inputs don't depend on each other's
  output belong in the same turn, not sequential round trips — this applies inside
  plan work exactly as it does everywhere else.
- **`/clear` (or a fresh session) between unrelated phases is safe and encouraged**
  once the current phase's state is actually persisted to Dibs — that's the entire
  point of resuming cold from there. Don't carry a large, no-longer-needed
  exploration context into an unrelated next phase just because the session happens
  to still be open.
- **Push deterministic checks to scripts/tools that return pass/fail + errors**, not
  narrated tool output — a lint/type-check/test run belongs in a `todo_comment` as
  "passed" or "3 failures: <what>", not as a transcript of the run.

---

## Git

Use git to keep a clear record of implementation changes. Before delegating,
establish the project repository and inspect its initial state. After each worker
iteration: `git status`, `git diff`, `git log` — review for unrelated modifications.
Workers may commit when appropriate, but a commit doesn't eliminate the need for
orchestrator review. Never reset, discard, or overwrite user work without explicit
justification.

## Code Review

The orchestrator independently reviews every worker result for: correctness,
requirements compliance, security, privacy, error handling, edge cases,
maintainability, performance, portability, test coverage, and accidental unrelated
changes — pay particular attention to assumptions about external data. If the
implementation is incorrect: document the issue as a `todo_comment` on the task
issue (or `todo_create` a new task under the plan if it's genuinely separate work),
launch the worker again with that context. Don't just say "fix it" without defining
what's wrong.

## Testing

Run tests after meaningful implementation steps. Don't accept "tests pass" without
knowing what was actually tested — see this machine's global sad-path-coverage rule,
which applies here too. Where external/user data is involved: use fixtures for
automated tests, avoid requiring private user data for normal test runs, keep real
user data read-only, and never embed sensitive data into the repository.

## Privacy

Do not unnecessarily copy, persist, print, or commit user prompts, source code,
credentials, API keys, tokens, personal information, or private project data. Process
metadata rather than storing underlying content when only metadata is required.
Review logs/debugging output for accidental sensitive information before they
persist anywhere.

## Scope Control

Don't expand the project because an interesting improvement surfaced mid-task.
Separate required functionality from useful-but-deferred functionality from unrelated
ideas; record deferred improvements if they're likely to matter later; keep the
current implementation focused.

## Final Completion

A plan is complete only when:

1. All required plan tasks are `done`.
2. Acceptance criteria are satisfied.
3. Tests/checks pass.
4. The orchestrator has independently reviewed the implementation.
5. No known critical blockers remain.
6. The working tree contains only intentional changes.
7. Important limitations are documented.
8. The plan issue itself is closed (`todo_complete`/`todo_revise` to final state)
   once the user confirms it's genuinely finished — not just paused. No separate
   archiving step: a closed issue already reads as done, per
   [Completion](#completion).

The final report summarizes what was built, important architectural decisions, how
it was verified, known limitations, and relevant future improvements. Don't claim
functionality that wasn't actually verified.
