# Plans, Dibs state, research and lessons

Reference for the `orchestrator-worker` skill; read it when the decision tree in `SKILL.md` points here.

## When This Applies

**Create a plan** (a `plan`-labeled issue, via `todo_scaffold_plan`) when the task is explicitly
multi-phase, an audit, framed as a todo list, or expected to span sessions. Skip it for single-turn,
single-file work; persistent mutation still needs a claimed task [rule 727] (a temporary task for ad hoc
changes). When unsure, create the plan: one call, cheap to leave nearly empty.

**Escalate to delegation** (workers, [Model Tiering](model-routing.md#model-tiering)) when the footprint is
large, subtasks are independent, or a cheaper model plausibly handles a bounded piece. Do it
automatically when clear, with one quick check-in when ambiguous, never silently. Most solo work stays
solo after it clears the plan bar.

## Project Isolation

Work inside the project directory. Read external data as read-only; never modify unrelated files,
repositories, configuration, credentials or user data.

## Project State

Multi-step work lives in **Dibs** (MCP server `dibs`; CLI fallback
`docker compose -f ~/www/dibs/docker-compose.yml exec -T -u www-data app php artisan todo:agent:<command>`).
Other tools register the MCP server in their own config. Do not call `todo_status` just to check the
connection; the first real call shows it, and a failure is reported with `todo_report_bug`.

A **plan** is a `plan`-labeled issue; its **tasks** are child issues (`todo_scaffold_plan` creates plan and
children atomically; `todo_create(parentId)` adds more). The local Dibs id is the task ID.

**Before starting work that might already have a plan:** `todo_context` and `todo_list label=plan` (scoped
to the project's Group); if a matching open plan exists, ask which to resume, then `todo_show` it. Scaffold
a new plan only for a distinct objective. File it under the matching area and Group (`newGroupName` makes
one); ask when Work vs Personal Projects is unclear. Concurrent plans need no registry; two plans touching
the same files should be one plan or sequenced.

### Plan body

The plan body is the authoritative plan: objective, decisions, dependency order, status, completion gates.
Revise it with `todo_revise` (a stale write returns `{conflict: true, current}`; reread and reconcile).
Task state is the status field: `CLOSED` done, live claim in progress, `OPEN` unclaimed pending; use a
comment or the `waiting` label for a blocked task. Do not close a task because a worker says it is done;
check the plan's acceptance criteria first (the orchestrator's job).

Break the plan into child tasks as soon as scope is known, even for solo work: one child per concrete
step, closed with `todo_complete`. A prose progress comment is not a substitute. Add children if scope grows.

### Checkpoints, questions, and results

All are `todo_comment` calls: on the plan for whole-plan matters (current step, worker model and cost,
decisions, limitations, blockers), on the task for task-scoped ones (blocker, result, verification; see
[Worker Questions and Blockers](roles-and-workers.md#worker-questions-and-blockers)). Concise checkpoints,
not a narration log; the body is canonical, comments are evidence.

A bug in the Dibs tooling itself is not a plan question: file it with `todo_report_bug` instead of working
around it.

### Task claims

**Claude Code with the dotfiles hooks: use the ```` ```dibs ```` block [rule 1307].** Write `dibs <id>` to claim
before editing; put `note`, `append`, `done` and `atlas` lines in a block at the end of the reply. The hook
applies them at Stop and renews the claim. The MCP calls below are the path for other agents, workers
without the hooks, and anything the block refuses.

`todo_claim` binds a claim to the worker's OS process (see Dibs `docs/agent-interface.md`); two workers
cannot claim one task, and a dead process's claim is recoverable. Keep the capability token for
`todo_heartbeat`, `todo_release` and `todo_complete`. Heartbeat on long tasks. `todo_complete` closes,
posts the summary and releases; `todo_release` abandons so another worker can start at once.
`todo_claim_status` reads a claim without holding one.

**Check claim status before starting any task, solo work too.** If another live process holds it
(`isCurrentlyAlive`), it is off-limits: pick another task without asking. Unexplained uncommitted changes
mid-plan mean check claim status first, never overwrite or finish someone else's edit.

### Scratch work

Session hand-offs are `todo_create(temporary: true)` tasks labelled `handoff`, parented to the plan; body
template, receiver protocol and discovery query live in skill `session-handoff` (`/handoff` runs it).
Durable decisions stay on the plan. Temporary tasks are deleted on completion, excluded from plan and
atlas accounting; consume temporary children first; `NOT_PLANNED` discards. Throwaway scripts and diffs
stay in the session scratchpad, not Dibs.

### Completion

A plan is done when every task is closed with satisfied criteria. `todo_revise` the body to the final
status, then `todo_complete` the plan. A closed issue stays discoverable via `todo_list(state: 'ALL')`.

## Shared Research Cache

Findings that outlive a plan live as `research`-labeled Dibs issues (title = topic), filed under Personal
Projects, "AI workflows" Group unless specific to one project (then that project's Group). When tied to
files, the body carries a `covers` list:

    covers:
      - path: <file path>
        hash: <git hash-object output, or sha256:<digest> for untracked files>

A topic without `covers` (a general fact) is trusted until revised.

**Before any research** (inline, forked or delegated), `todo_search` or `todo_list label=research` for the
topic. With a `covers` list: re-hash each file; all match, reuse and cite the issue; a few changed,
delegate a narrow re-verify of those diffs and `todo_revise`; most changed or scope shifted, redo it fully
and `todo_revise` wholesale. **After research** (cache hit or fresh) `todo_create` or `todo_revise` the
record; skipping the write-back defeats the cache.

## Shared Lessons Store

Durable non-code-specific knowledge (gotchas, platform quirks, logic traps, snippets) lives as
`lesson`-labeled issues, same placement as research. Lessons need no `covers`: they describe how something
outside the codebase behaves, so they only go stale when the tool or platform changes. **Before** touching
a gotcha-prone domain, search `label=lesson`; **after** learning something durable, `todo_create` or
`todo_revise` it. A lesson is cross-project by construction.

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

The orchestrator decides what needs answering; delegate the gathering when it is substantial (several
files, broad grep, many exploratory commands, an external API). A single quick lookup is cheaper inline.
Check the [Shared Research Cache](plans-and-state.md#shared-research-cache) first; a hit skips delegation.

Group related questions into one research worker; run independent ones in parallel
([Parallel vs Sequential Workers](launching-workers.md#parallel-vs-sequential-workers)). Use the cheapest
capable model.

**Fork or fresh agent:** a fork inherits your context and prompt cache but always runs on your model; a
fresh agent starts cold but can be cheaper ([Model Tiering](model-routing.md#model-tiering)). Pick by which
cost dominates, context re-derivation or per-token price.

Research workers need no task id or full worker protocol: the question, read-only, plus the instruction to
check and update the research and lesson records. Cross-tool ones get the
[worker session tag](launching-workers.md#worker-session-tagging) as their first line, with `research` in
place of a task id.

```
You are a RESEARCH WORKER in the orchestrator/worker protocol (skill: orchestrator-worker, or read
~/dotfiles/ai/skills/orchestrator-worker/SKILL.md).

Project: <absolute path>
Plan: Dibs issue #<plan issue id>
Research question(s): <specific and bounded>

First search Dibs (label=research, then label=lesson) and reuse or narrowly re-verify what exists.
Investigate read-only. Report concisely: findings, where (paths, line numbers, commands), what you could
not confirm, and your agent type and model. Write durable findings as a research-labeled issue (with a
covers list) and non-code gotchas as lesson-labeled ones; also todo_comment on the plan if useful. Use
todo_report_bug if the Dibs tooling misbehaves.
```

**Trust, but verify what matters.** Spot-check any finding the plan critically depends on, including a
cache hit: a matching hash means the file is unchanged, not that the original finding was right.

## Task Decomposition

Tasks should be independently understandable, bounded, testable and small enough for a worker to finish
without losing context. Not too large ("build the feature"), not too small ("rename a variable"). Typical
units: "document the input format", "implement the parser for format X", "add validation for case Y",
"add tests for malformed input".
