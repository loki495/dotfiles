---
name: orchestrator-worker
description: Orchestrator/worker delegation protocol for splitting expensive planning-and-review reasoning from cheap, bounded execution. The orchestrator plans, decomposes, delegates, and reviews using the strongest available model; workers each execute one bounded task using a cheaper/faster model. Communication is file-based (.ai/PLAN.md, STATE.md, QUESTIONS.md, RESULT.md), so it works whether the orchestrator and worker are the same tool, different tools (Claude Code, opencode, Codex, agy), or different sessions entirely. Use when a task is complex enough to warrant explicit planning plus delegated implementation, or when you want an expensive model's usage confined to reasoning rather than mechanical execution.
---

# Orchestrator/Worker Protocol

Tool-agnostic. Any of Claude Code, opencode, Codex, or Antigravity's `agy` can play
either role — orchestrator in one project, worker in another, sometimes both in the
same run (see [Launching Workers](#launching-workers)). Nothing here assumes a
specific tool; where mechanics differ per tool, that's called out explicitly.

## Core principle

    investigate
        |
      plan
        |
    delegate
        |
     worker  <--- cheap/fast model, one bounded task
        |
   +----+----+
   |         |
complete   blocked
   |         |
   |      question
   |         v
   |    orchestrator  <--- expensive/strong-reasoning model
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

## Role: Orchestrator

The orchestrator is the senior agent responsible for:

- understanding the overall objective;
- investigating the environment and repository;
- creating and maintaining the implementation plan;
- decomposing work into bounded tasks;
- delegating implementation to workers;
- reviewing worker results;
- resolving worker questions and blockers;
- deciding when additional worker iterations are required;
- performing final validation and review.

The orchestrator is **not** the primary implementation worker. It should generally
avoid implementing application code itself — its job is to direct, review, and make
architectural decisions. See [Model Tiering](#model-tiering) for why this split
exists, not just as a division of labor.

## Role: Worker

A worker is an implementation agent responsible for:

1. Reading this protocol (see [Worker Context](#worker-context)).
2. Reading the current plan and state.
3. Identifying its assigned task.
4. Inspecting relevant code/data itself — not just trusting the orchestrator's
   description of it.
5. Implementing the task.
6. Running appropriate tests/checks.
7. Updating task status.
8. Recording relevant results.
9. Reporting completion or blockers.

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

Every orchestrated project maintains four files at its root:

    .ai/PLAN.md
    .ai/STATE.md
    .ai/QUESTIONS.md
    .ai/RESULT.md

These are the **authoritative** communication channel. A worker's direct response —
whatever the launching tool returns immediately after the call — is a convenience for
the orchestrator's next step, nothing more. If it ever conflicts with what these files
say, the files win; fix the files if they're wrong. Any orchestrator (even a fresh
session, even a different tool) must be able to resume a project from these four files
alone, with no memory of prior conversation.

Only the orchestrator writes to `STATE.md`. Workers append to `QUESTIONS.md` and
`RESULT.md`, and update only their own task's status line in `PLAN.md` — this matters
once workers run in parallel (see [Parallel vs Sequential Workers](#parallel-vs-sequential-workers)).

### PLAN.md

The authoritative implementation plan. Each task/step contains:

- ID
- objective
- relevant files
- dependencies
- acceptance criteria
- implementation notes
- status: `pending` / `in_progress` / `blocked` / `needs_review` / `done`

Do not mark a task `done` merely because the worker claims completion — the
acceptance criteria must actually be satisfied. That check is the orchestrator's job.

### STATE.md

The current orchestration state, kept concise and current:

- current objective;
- current step;
- current worker status;
- worker model (exact provider/model identifier — see [Model Tiering](#model-tiering));
- important architectural decisions;
- known limitations;
- outstanding blockers.

### QUESTIONS.md

The communication channel for worker questions and blockers. A question needs enough
context for the orchestrator to decide without reconstructing the worker's entire
thought process (see [Worker Questions and Blockers](#worker-questions-and-blockers)).

### RESULT.md

A durable record of meaningful discoveries and results: important findings about
external data, architectural decisions, unexpected constraints, completed worker
iterations, significant implementation decisions, verification results. Not a
narration log — record what matters, not every step taken.

---

## Planning

Before delegating any implementation:

1. Inspect the repository and relevant environment.
2. Investigate external/local data the project depends on — inspect the actual
   format rather than assuming it; if an external application's format changes
   later, the project should fail safely rather than silently produce misleading
   results.
3. Identify important constraints and unknowns; document uncertainties rather than
   treating assumptions as facts.
4. Create a concrete implementation plan.
5. Define acceptance criteria.
6. Identify dependencies between tasks.
7. Only then begin delegating.

Prefer evidence from the actual environment over memory or generic documentation. The
plan must be detailed enough that a worker can execute a bounded step without the
orchestrator's full conversation history — because it won't have it.

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
- `.ai/PLAN.md`, `.ai/STATE.md`, `.ai/QUESTIONS.md` in the project directory.

The worker inspects the repository itself rather than relying entirely on the
orchestrator's description, and must not assume the plan is correct if repository
evidence contradicts it — when it finds a contradiction, it stops and asks (see
below).

### Worker prompt template

Use this as the starting point for every worker launch, filled in per task:

```
You are a WORKER in the orchestrator/worker protocol
(skill: orchestrator-worker, or read
~/dotfiles/ai/skills/orchestrator-worker/SKILL.md if not auto-loaded).

Project: <absolute path>
Your task: <task ID from PLAN.md>

Before doing anything:
1. Read .ai/PLAN.md, .ai/STATE.md, and .ai/QUESTIONS.md in the project directory.
2. Confirm your assigned task and its acceptance criteria.
3. Inspect the actual code/data yourself.

Then implement the task and follow the Worker Completion Protocol, or the Worker
Questions and Blockers protocol if you hit something you must not guess on.
```

---

## Worker Completion Protocol

When a worker successfully completes a task:

1. Verify the acceptance criteria are actually satisfied.
2. Run appropriate tests/checks.
3. Mark the task `done` in `PLAN.md`.
4. Update `STATE.md` if relevant to the overall state (the orchestrator should
   confirm/finalize this on review, not treat the worker's edit as final).
5. Record meaningful results in `RESULT.md`.
6. Return a concise completion report covering: what changed, what was tested, any
   assumptions made, any remaining concerns.

A worker's `OK` is not sufficient evidence the task is correct — the orchestrator
independently reviews every result (see [Code Review](#code-review)).

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

1. Mark the current task `blocked` or `needs_review` in `PLAN.md`.
2. Write the question to `.ai/QUESTIONS.md`: what was discovered, why the plan
   can't safely continue, exactly what decision/information is needed, options if
   useful, a recommendation if there is one.
3. Leave the working tree in a coherent state.
4. Stop and return control to the orchestrator.

## Blocker Resolution Loop

1. The orchestrator reads the question, investigates if necessary, and makes the
   decision.
2. Records the answer in `QUESTIONS.md`.
3. Updates `PLAN.md` if the plan changes, and `STATE.md`.
4. Launches a worker again (fresh — it has no memory of the earlier attempt beyond
   what's in the files), telling it to continue from the blocked task.

Do not restart the whole project over one blocker. A task cycling through
`worker -> blocked -> orchestrator decision -> worker -> done` is normal, not a
failure — a worker surfacing something the orchestrator missed is the protocol
working as intended.

---

## Model Tiering

The orchestrator and the worker do fundamentally different work and should normally
run different-cost models — this is the point of the split, not an incidental detail:

- **Orchestrator**: plans, decomposes, resolves ambiguity, reviews correctness. Use
  the strongest available reasoning model even though it costs more per token —
  there's normally only one orchestrator running at a time, so the cost is bounded
  and the work genuinely needs the reasoning.
- **Worker**: executes one already-decomposed, bounded task. Default to the
  cheapest/fastest model that can reliably do it. Workers run more often, and
  sometimes in parallel, so their per-token cost is what actually compounds — this is
  where token spend is controlled.

Bump a worker to a stronger model only when the bounded task itself genuinely
requires deep reasoning (diagnosing a subtle bug, reconciling conflicting
constraints) — not by default "to be safe." Record the exact worker model in
`STATE.md` either way. Don't assume a model's cost or availability from its name;
verify with the tool's own model listing before launching (`opencode models`,
`codex debug` / `-c model=...` docs, `agy models`, etc.).

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
| opencode | `opencode run --model <provider/model> "<worker prompt>"` | `--model` | Foreground subprocess; cwd = project dir. Verify exact syntax with `opencode run --help` / `opencode models` — do not invent provider/model names. |
| Codex | `codex exec -m <model> "<worker prompt>"` (alias `codex e`) | `-m`/`--model` | Foreground subprocess. Verify with `codex exec --help`. `codex agents` lists sessions on the local app-server daemon if you need to check on a running one. |
| agy (Antigravity) | `agy -p --agent <name> --model <model> "<worker prompt>"` | `--model` | Foreground subprocess (`-p`/`--print` = non-interactive). `--effort` isn't supported on every model. agy has account-wide usage quotas — check headroom before launching several workers in a row. |

Claude Code is the one exception, since the orchestrator is usually already running
inside it: use the `Agent` tool directly rather than shelling out to `claude -p`.
Pick a `subagent_type` (a purpose-built agent, or `general-purpose`), pass the worker
prompt as `prompt`, and use the `model` parameter to pin the cheaper tier. Runs
synchronously by default (the report comes back in the tool result); use
`subagent_type: "fork"` with background execution when launching workers in parallel
(see below) so their tool output doesn't fill the orchestrator's own context.

Confirmed as of 2026-08-29 against the installed versions on this machine — CLI flags
drift between releases, so re-verify with the tool's own `--help` if it's been a
while.

### Parallel vs Sequential Workers

Sequential is the default: one task's result often changes what the next task should
be, and it keeps the `.ai/` files a single source of truth with no concurrent writers.

Launch workers in parallel only when:

- the tasks are genuinely independent — no shared files, no dependency listed in
  `PLAN.md`;
- each worker has a distinct, bounded slice of work with no overlapping writes;
- the orchestrator will review each result independently before marking it done.

When running parallel workers, give each a distinct task ID and instruct it to touch
only files within its own task's scope. Only the orchestrator writes `STATE.md`;
parallel workers append to `QUESTIONS.md`/`RESULT.md` and update only their own task's
status line in `PLAN.md`, to avoid clobbering each other's writes.

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
implementation is incorrect: document the issue, create/update a task in `PLAN.md`,
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

A project is complete only when:

1. All required plan tasks are `done`.
2. Acceptance criteria are satisfied.
3. Tests/checks pass.
4. The orchestrator has independently reviewed the implementation.
5. No known critical blockers remain.
6. The working tree contains only intentional changes.
7. Important limitations are documented.

The final report summarizes what was built, important architectural decisions, how
it was verified, known limitations, and relevant future improvements. Don't claim
functionality that wasn't actually verified.
