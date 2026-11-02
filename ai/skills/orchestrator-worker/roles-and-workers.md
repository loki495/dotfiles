# Roles and the worker protocol

Reference for the `orchestrator-worker` skill; read it when the decision tree in `SKILL.md` points here.

## Role: Orchestrator

The orchestrator is the senior agent responsible for:

- understanding the overall objective;
- investigating the environment and repository;
- creating and maintaining the implementation plan;
- decomposing work into bounded tasks when delegating;
- delegating implementation to workers once escalated (see
  [When This Applies](plans-and-state.md#when-this-applies));
- reviewing worker results;
- resolving worker questions and blockers;
- deciding when additional worker iterations are required;
- performing final validation and review;
- telling the user, **before every worker launch** (not just when asked), which
  agent/tool and model it's about to use and why — see
  [Worker Launch Reporting](launching-workers.md#worker-launch-reporting).

For work that hasn't crossed the delegation threshold, the orchestrator does the
work directly rather than manufacturing a worker launch for its own sake — see
[When This Applies](plans-and-state.md#when-this-applies) and the "don't delegate a single quick
lookup" floor in [Research Delegation](plans-and-state.md#research-delegation). Once delegation is
warranted, the orchestrator should generally avoid implementing application code
itself — its job shifts to directing, reviewing, and making architectural
decisions. See [Model Tiering](model-routing.md#model-tiering) for why this split exists, not just
as a division of labor.

## Role: Worker

A worker is an implementation agent responsible for:

1. Reading this protocol (see [Worker Context](roles-and-workers.md#worker-context)).
2. Reading the current plan and state.
3. Identifying its assigned task.
4. Checking [Shared Research Cache](plans-and-state.md#shared-research-cache) and
   [Shared Lessons Store](plans-and-state.md#shared-lessons-store) for anything already known before
   investigating from scratch.
5. Inspecting relevant code/data itself — not just trusting the orchestrator's
   description of it.
6. Implementing the task.
7. Running appropriate tests/checks.
8. Updating task status.
9. Recording relevant results — as a `todo_comment` checkpoint on its task issue, and
   in the shared research/lessons knowledge records when applicable (see
   [Worker Completion Protocol](roles-and-workers.md#worker-completion-protocol)).
10. Reporting completion or blockers, and self-reporting via `todo_report_bug` if the
    Dibs tooling itself misbehaves along the way (distinct from a plan question —
    see [Worker Questions and Blockers](roles-and-workers.md#worker-questions-and-blockers)).

The worker should not redesign the project without consulting the orchestrator. It
may make reasonable local implementation decisions consistent with the plan; major
architectural decisions belong to the orchestrator.

## Worker Context

Every worker must be instructed, at minimum, to read:

- this protocol (the `orchestrator-worker` skill if the worker's tool auto-loads
  shared skills; otherwise point it explicitly at
  `~/dotfiles/ai/skills/orchestrator-worker/SKILL.md`);
- this plan's issue and its own task issue in Dibs (`todo_show` on each, per
  [Project State](plans-and-state.md#project-state)) — via the `dibs` MCP server if this worker's tool
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
[worker session tag](launching-workers.md#worker-session-tagging) as the literal first line, before
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
   `todo_create`/`todo_revise` it in [Shared Research Cache](plans-and-state.md#shared-research-cache).
   If it surfaced a durable non-code-specific gotcha, do the same in
   [Shared Lessons Store](plans-and-state.md#shared-lessons-store).
6. Return a concise completion report covering: what changed, what was tested, any
   assumptions made, any remaining concerns, and which agent/subagent type and model
   it actually ran as (confirms what was used, in case of a fallback from what the
   orchestrator requested).
7. Report cost — see [Cost Reporting](roles-and-workers.md#cost-reporting) for what's actually available
   to report and how to report it honestly.

This applies equally whether the step was done by a delegated worker or by the
orchestrator working directly on a light plan — whoever did the step closes/comments
the task, updates the plan issue, and updates the shared knowledge records, not just
workers.

A worker's `OK` is not sufficient evidence the task is correct — the orchestrator
independently reviews every result (see [Code Review](practices.md#code-review)).

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
