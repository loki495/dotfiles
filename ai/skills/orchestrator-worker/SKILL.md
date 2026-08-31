---
name: orchestrator-worker
description: Orchestrator/worker delegation protocol for splitting expensive planning-and-review reasoning from cheap, bounded execution. The orchestrator stays on whatever model it was launched with and plans, decomposes, delegates, and reviews; each worker runs on the cheapest model, in any available tool (Claude Code, opencode, Codex, agy), that's judged capable of its one bounded task — reported to the user with justification before every launch, never assumed from whatever's already running. Communication is file-based (.ai/PLAN.md, STATE.md, QUESTIONS.md, RESULT.md), so this works across tools and across sessions. Use when a task is complex enough to warrant explicit planning plus delegated implementation, or when you want an expensive model's usage confined to reasoning rather than mechanical execution.
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
- performing final validation and review;
- telling the user, **before every worker launch** (not just when asked), which
  agent/tool and model it's about to use and why — see
  [Worker Launch Reporting](#worker-launch-reporting).

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
- worker model, how it was launched (in-process, or cross-tool via which CLI), why
  that one was picked, and its cost as actually reported (exact or proxy — see
  [Cost Reporting](#cost-reporting)) — see [Model Tiering](#model-tiering) and
  [In-Process vs Cross-Tool](#in-process-vs-cross-tool);
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

1. Scaffold `.ai/PLAN.md`, `.ai/STATE.md`, `.ai/QUESTIONS.md`, `.ai/RESULT.md` in the
   project directory — they can start as stubs (`STATE.md` can just say
   "researching, no plan yet"). This gives research workers somewhere to log
   durable findings even before a plan exists.
2. Inspect the repository and relevant environment.
3. Identify what's actually unknown — specific questions, not "investigate
   everything." Anything that needs reading multiple files/sources or several
   exploratory commands is a candidate for delegating the gathering to a research
   worker rather than doing it inline (see [Research Delegation](#research-delegation)).
4. Identify important constraints and unknowns; document uncertainties rather than
   treating assumptions as facts.
5. Create a concrete implementation plan.
6. Define acceptance criteria.
7. Identify dependencies between tasks.
8. Only then begin delegating implementation.

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
costs more than it saves.

Group related questions into one research worker; split genuinely independent
questions into parallel workers (same reasoning as
[Parallel vs Sequential Workers](#parallel-vs-sequential-workers)). Use the same
cheap-model-by-default tiering as implementation workers — bump up only when the
question itself needs judgment to answer correctly, not brute-force lookup volume.

Research workers are lighter-weight than implementation workers: there's no
`PLAN.md` yet at this point, so they don't need a task ID or the full worker
protocol — just the question, read-only.

```
You are a RESEARCH WORKER in the orchestrator/worker protocol
(skill: orchestrator-worker, or read
~/dotfiles/ai/skills/orchestrator-worker/SKILL.md if not auto-loaded).

Project: <absolute path>
Research question(s): <specific and bounded — not "investigate the codebase">

Investigate read-only — do not modify anything. Report back concisely: what you
found, where (file paths/line numbers, commands run), and flag anything you
couldn't confirm rather than guessing. State which agent/subagent type and model
you ran as. If it's a durable finding worth keeping past this session, also append
it to .ai/RESULT.md.
```

**Trust, but verify what matters.** Treat a research worker's findings as reliable
for minor/local facts. For anything the plan critically depends on — a claim that,
if wrong, would derail multiple downstream tasks — spot-check it yourself before
committing to the plan. A wrong implementation usually fails a test; a wrong research
finding just quietly becomes a wrong plan, so it doesn't get the same automatic
safety net.

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
Questions and Blockers protocol if you hit something you must not guess on. Include
which agent/subagent type and model you ran as, and your cost per Cost Reporting, in
your report.
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
   assumptions made, any remaining concerns, and which agent/subagent type and model
   it actually ran as (confirms what was used, in case of a fallback from what the
   orchestrator requested).
7. Report cost — see [Cost Reporting](#cost-reporting) for what's actually available
   to report and how to report it honestly.

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
  this plainly in `RESULT.md` rather than omitting a cost line silently; a known gap
  is more useful than a missing one.

Record whatever was actually captured — exact or proxy — in `STATE.md` alongside the
model/mechanism/justification already required there, so a long session accumulates a
readable cost trail instead of requiring a transcript dig to reconstruct later.

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
by itself, even before comparing model prices.

Bump a worker to a stronger model only when the bounded task itself genuinely
requires deep reasoning (diagnosing a subtle bug, reconciling conflicting
constraints) — not by default "to be safe," and not just because it's the model
already running. Whichever model gets picked, state *why* — "cheapest capable option
available" is a real justification, but it has to have actually been checked against
the alternatives, not assumed. Record the exact worker model, which tool it ran in,
and that justification in `STATE.md`. Don't assume a model's cost or availability
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
| opencode | `opencode run --model <provider/model> "<worker prompt>"` | `--model` | Foreground subprocess; cwd = project dir. Verify exact syntax with `opencode run --help` / `opencode models` — do not invent provider/model names. |
| Codex | `codex exec -m <model> "<worker prompt>"` (alias `codex e`), add `--json` to capture real usage — see [Cost Reporting](#cost-reporting) | `-m`/`--model` | Foreground subprocess. Verify with `codex exec --help`. See [Background Launch Verification](#background-launch-verification) before ever backgrounding a codex (or any cross-tool) worker without waiting on it — `codex agents` needs a real TTY and cannot be used from a script. |
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

### Background Launch Verification

A real orchestration run hit a genuine race: two `codex exec` workers were launched,
the launching harness reported both complete, but both were still writing output
minutes later — a concurrent write corrupted `PLAN.md`'s status section until the
stray processes were killed and the files manually reconciled. Investigated in two
passes: a live test of a single, properly-waited `codex exec` call (2026-08-30), then
later a direct read of the actual incident transcript (2026-08-30), which found the
exact cause.

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
2. **Require a completion sentinel, not just a process-exit signal**, whenever a
   worker does run in the background. Have the worker's prompt end with an explicit
   instruction to write a fixed final line to its own `RESULT.md` as its last action
   (e.g. `WORKER_DONE <task-id>`). The orchestrator treats the worker as finished only
   once that sentinel is actually present on disk — not merely because the launching
   call returned or a background-task notification fired. This restates
   [Worker Completion Protocol](#worker-completion-protocol)'s existing file-based
   verification, called out explicitly here because this exact gap has already caused
   real file corruption once.
3. **Poll for the sentinel** (a short loop checking `RESULT.md` for the marker)
   rather than relying on a single "done" event — see the Monitor tool's guidance on
   polling loops if launching from Claude Code.
4. **If a stray process is still visible after the sentinel appears**, don't assume
   it's hung — disk writes can trail the sentinel by a few seconds. Recheck after a
   short pause before concluding it's actually stuck. Only kill a process that's
   clearly well past the task's expected size, and always re-read (don't assume) any
   `.ai/` files it touched afterward, the same way the original incident was
   recovered from.
5. **Give each parallel cross-tool worker its own project directory** (`-C <dir>` or
   equivalent, per [Project Isolation](#project-isolation)) — this narrows, though
   doesn't by itself eliminate, the chance of state bleeding between concurrent
   workers sharing one tool's backend.

### In-Process vs Cross-Tool

Communication is entirely file-based, so it doesn't matter to the protocol whether a
worker runs in-process (the orchestrator's own `Agent`/subagent mechanism) or as a
separate cross-tool subprocess (`opencode run`, `codex exec`, `agy -p`) — either way
the worker reads `.ai/PLAN.md`/`STATE.md`/`QUESTIONS.md` and reports back through the
same files. The orchestrator never needs tool-specific handling once a worker is
launched; it just watches for file updates and the return value like any other
worker.

**Prioritize the cheapest capable model for every worker, in-process or not** — don't
default to in-process just because it's already open. The in-process/cross-tool
question is purely mechanical (how do I reach the cheapest capable option), not a
reason to skip looking for it.

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

Record which mechanism was actually used, alongside the model, in `STATE.md`.

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
