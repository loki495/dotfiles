---
name: orchestrator-worker
description: Default file-based protocol for any multi-step coding work — solo, forked, or delegated to workers. A plan lives in its own folder under .ai/plans/<plan-slug>/ (PLAN.md, STATE.md, QUESTIONS.md, RESULT.md, scratch/), created automatically once work is explicitly multi-phase or spans sessions, so a fresh session (this one resuming later, or a different tool entirely) can pick it up cold from the files alone. Small work escalates to full delegation (workers, model tiering, parallel execution) automatically when it's clearly warranted, or with a quick check when it's ambiguous — never silently. Two shared, cross-plan stores back every plan: .ai/research/ (checksum-versioned investigative findings, reused until the files they're based on change) and .ai/lessons/ (durable non-code gotchas — platform quirks, library fine print, logic traps — checked before and updated after any research or implementation step). Tool-agnostic throughout: Claude Code, opencode, Codex, and agy can each play orchestrator or worker, and every file here is plain text any of them can read and write. Use this by default for multi-step work, not only when explicitly asked.
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

**Create a plan folder** (`.ai/plans/<plan-slug>/`) when the task is:

- explicitly multi-phase, an audit, or framed as a plan/todo list by the user;
- expected to span more than one session (paused and resumed later, possibly by a
  different session or tool);
- work I would already reach for the in-session `TodoWrite` tool for, **and** it
  needs to survive a session boundary rather than just this conversation.

Skip the folder for single-turn, single-file, quickly-resolved work — a plain reply
or an ordinary `TodoWrite` list is enough, and creating a folder for a three-line fix
is pure overhead. When genuinely unsure whether a task clears this bar, err toward
creating the folder — cheap to create, cheap to leave nearly empty, expensive to
reconstruct provenance for later if skipped and the task turns out to run long.

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
delegation partway through, that's normal; nothing about the folder structure
changes, only how heavily its files get used (see [Project State](#project-state) —
every plan gets all four files from creation, light or not).

A plan that never needs delegation is not a failure of the protocol — most solo
work, once it clears the "create a folder" bar, stays solo the whole way through.

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
9. Recording relevant results — in `RESULT.md`, and in the shared research/lessons
   stores when applicable (see [Worker Completion Protocol](#worker-completion-protocol)).
10. Reporting completion or blockers.

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

A project can have more than one plan active, paused, or completed at once —
different objectives, launched by different sessions, sometimes at the same time.
Each gets its own folder so they can't collide, and so any session — this one
resuming later, or a completely different one — can find and pick up exactly where
another left off:

    .ai/plans/INDEX.md                    <- registry of every plan
    .ai/plans/<plan-slug>/PLAN.md
    .ai/plans/<plan-slug>/STATE.md
    .ai/plans/<plan-slug>/QUESTIONS.md
    .ai/plans/<plan-slug>/RESULT.md
    .ai/plans/<plan-slug>/scratch/
    .ai/plans/archive/<plan-slug>/        <- completed plans, moved here after confirmation

**`<plan-slug>`**: `<YYYY-MM-DD>-<kebab-slug-of-the-objective>`, e.g.
`2026-08-30-cards-domain-migration`. Human-readable, sorts naturally by date, and only
collides if two plans started the same day land on the same slug — if that
happens, make the slug more specific rather than appending an arbitrary suffix.

**Before starting work on a project that has `.ai/plans/`, always check for existing
plans first** — don't assume the directory is empty or that this is a fresh start:

1. Read `INDEX.md` if it exists (or list `.ai/plans/*/` if it doesn't yet — a folder
   can exist without ever having been indexed, if whatever created it was
   interrupted before writing its row).
2. If an entry matches the requested objective and isn't `done`, ask which to resume
   rather than assuming — then read its four files and continue from `STATE.md`'s
   current step. A new session has no memory of the old one, but the files are the
   authoritative record — that's the entire point of this being file-based rather
   than conversation-based.
3. Only create a new `<plan-slug>` folder for a genuinely distinct objective.

**`INDEX.md`** is a flat list, one line per plan:

    - <plan-slug> | <status> | <one-line objective> | updated <date>

Each orchestrator only ever writes its own line — never edit another plan's row,
even to fix formatting, the same way parallel workers only touch their own status
line in `PLAN.md` (see [Parallel vs Sequential Workers](#parallel-vs-sequential-workers)).
Add a line when creating a folder; update only your own line's status/date as things
progress.

Multiple plans can run concurrently in the same project as long as their scopes
don't overlap. If two plans would touch the same files, that's a sign they should be
one plan, or sequenced, rather than two independent ones — check `INDEX.md` for that
before starting a second one that might collide with a still-active first.

The four files inside a plan's own folder are the **authoritative** communication
channel for that plan. A worker's direct response — whatever the launching tool
returns immediately after the call — is a convenience for the orchestrator's next
step, nothing more. If it ever conflicts with what these files say, the files win;
fix the files if they're wrong. Any orchestrator (even a fresh session, even a
different tool) must be able to resume a plan from its four files alone, with no
memory of prior conversation.

Only the orchestrator writes to `STATE.md`. Workers append to `QUESTIONS.md` and
`RESULT.md`, and update only their own task's status line in `PLAN.md` — this matters
once workers run in parallel (see [Parallel vs Sequential Workers](#parallel-vs-sequential-workers)).

Every plan gets all four files from creation, even a light one that never needs
delegation — they can start as stubs (`STATE.md` can just say "researching, no plan
yet"). What "graduating to full delegation" changes is how heavily these files get
used (worker launches, cost reporting, parallel coordination), not whether they
exist. This keeps a plan from ever needing to move or be restructured mid-flight —
see [When This Applies](#when-this-applies).

### PLAN.md

The authoritative implementation plan. Each task/step contains:

- ID
- objective
- relevant files
- dependencies
- acceptance criteria
- implementation notes
- status: `pending` / `in_progress` / `blocked` / `needs_review` / `done`

A light plan's tasks can be simple checkbox-style entries without every field filled
in — the format scales down, it doesn't need a separate lighter file.

Do not mark a task `done` merely because the worker (or your own direct work) claims
completion — the acceptance criteria must actually be satisfied. That check is the
orchestrator's job.

### STATE.md

The current plan state, kept concise and current:

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

A durable record of meaningful discoveries and results **for this plan specifically**:
important findings about external data, architectural decisions, unexpected
constraints, completed worker iterations, significant implementation decisions,
verification results. Not a narration log — record what matters, not every step
taken. Findings that outlive this plan — reusable investigative facts, or durable
non-code gotchas — belong in [Shared Research Cache](#shared-research-cache) or
[Shared Lessons Store](#shared-lessons-store) instead (or as well, if genuinely both
plan-specific context and reusable knowledge).

### scratch/

Exploration notes, generated one-off scripts, temp diffs, working files that support
the plan but aren't meant to become permanent project files. Not part of the
authoritative record — `RESULT.md` is. Safe to be messy; safe to gitignore
(`.ai/plans/*/scratch/` is a reasonable project `.gitignore` entry, added via
`/project-bootstrap` or by hand — not required, but the four top-level files are
committed by convention and `scratch/` deliberately is not).

### Archiving

When a plan is marked `done` in `INDEX.md` and the user confirms it's genuinely
finished (not just paused), move its folder to `.ai/plans/archive/<plan-slug>/` and
update its `INDEX.md` line's status to `archived`. Don't auto-archive without that
confirmation — a "done" plan sometimes gets reopened, and archiving is a courtesy for
keeping the active list scannable, not a hard deletion.

---

## Shared Research Cache

`.ai/research/` holds investigative findings that outlive any single plan — about
this codebase specifically, or about general technical facts (a library's behavior,
an API's shape, a format's quirks) — so the next plan, any plan, any tool, doesn't
re-investigate something already answered.

    .ai/research/INDEX.md
    .ai/research/<topic-slug>.md

**`INDEX.md`**, one line per topic:

    - <topic-slug> | <keywords> | <files/paths this topic covers> | verified <date>

**`<topic-slug>.md`**, a small header plus the findings:

    ---
    topic: <topic-slug>
    covers:
      - path: <file path>
        hash: <git hash-object output, or sha256:<digest> for untracked files>
      - path: <file path>
        hash: <...>
    updated: <date>
    ---

    <findings — concise, information-dense, written for a cold reader>

A topic with no `covers` entries (a general fact not tied to specific files — how a
library behaves, an API contract) has no hash to check and is simply trusted until
manually revised, same as [Shared Lessons Store](#shared-lessons-store).

**Before any research** — inline, forked, or delegated to a worker — check
`.ai/research/INDEX.md` for a matching topic first. If one exists with `covers`
entries:

1. Re-hash each listed file (`git hash-object <path>` for tracked files; `sha256sum`
   for untracked ones — cheap, exact, no need to read full file content to compute).
2. All hashes match → reuse the cached findings directly, cite the topic file, skip
   new research entirely.
3. A few files changed → delegate a narrow re-verify scoped only to the diff of
   those files (cheap — this is not a full re-research), then patch the note's
   affected sections, hashes, and `updated` date.
4. Most or all files changed, or the topic's actual scope has clearly shifted →
   treat the note as stale, do full research, overwrite.

**After any research** — whether it hit the cache or ran fresh — write or update the
topic's entry in both `INDEX.md` and its own file. This is what makes the cache
actually pay off on the next plan; skipping the write-back defeats the point.

---

## Shared Lessons Store

`.ai/lessons/` holds durable, **non-code-specific** knowledge: gotchas, edge cases,
fine-print behavior, platform/OS quirks, logic or math traps, tips and snippets —
things that don't go stale when this codebase's files change, only when the
underlying tool, platform, or understanding changes. This is the key distinction
from [Shared Research Cache](#shared-research-cache): research is versioned against
file hashes because code changes invalidate it; lessons aren't, because they're not
about this code's current state, they're about how something outside this codebase
actually behaves.

    .ai/lessons/INDEX.md
    .ai/lessons/<topic-slug>.md

**`INDEX.md`**, one line per topic:

    - <topic-slug> | <keywords/tags> | <one-line hook>

**`<topic-slug>.md`**:

    ---
    topic: <topic-slug>
    tags: [php, laravel, opencart, bash, os, general, ...]
    ---

    <the gotcha, concise, information-dense>

**Before** research or implementation touching something that smells like a gotcha
domain (an unfamiliar library, OS-specific behavior, a math/logic edge case, a
platform quirk) — check `.ai/lessons/INDEX.md` for a matching topic. **After**
discovering something durable and non-code-specific worth keeping — write it, in
both `INDEX.md` and its own topic file.

Scoped to the current project for now (`.ai/lessons/` at the project root). When a
lesson is clearly general-purpose — not tied to this codebase or business logic at
all — flag it and offer to also save it to a machine-wide location, the same way
global `CLAUDE.md`'s memory-scope-discipline rule already handles workflow
preferences that turn out to be general rather than project-specific. Don't do this
silently; ask, the same as that rule does.

---

## Planning

Before delegating any implementation:

1. Check `.ai/plans/INDEX.md` for an existing, unfinished plan on this objective
   before creating a new one (see [Project State](#project-state)). If starting
   fresh, pick a `<plan-slug>`, add its row to `INDEX.md`, and scaffold `PLAN.md`,
   `STATE.md`, `QUESTIONS.md`, `RESULT.md`, `scratch/` in its folder — they can start
   as stubs. This gives research even before a plan exists somewhere durable to land.
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

Research workers are lighter-weight than implementation workers: there's no
`PLAN.md` yet at this point, so they don't need a task ID or the full worker
protocol — just the question, read-only, plus the instruction to check and update
the shared research/lessons stores. Cross-tool research workers still get the
[worker session tag](#worker-session-tagging) prepended as their literal first line
(use `<task-id>=research` since there's no real task ID yet); in-process ones skip it.

```
You are a RESEARCH WORKER in the orchestrator/worker protocol
(skill: orchestrator-worker, or read
~/dotfiles/ai/skills/orchestrator-worker/SKILL.md if not auto-loaded).

Project: <absolute path>
Plan: .ai/plans/<plan-slug>/
Research question(s): <specific and bounded — not "investigate the codebase">

First check .ai/research/INDEX.md and .ai/lessons/INDEX.md for anything already
known about this — reuse or narrowly re-verify per Shared Research Cache rather than
starting from scratch if a matching topic exists.

Investigate read-only — do not modify anything. Report back concisely: what you
found, where (file paths/line numbers, commands run), and flag anything you
couldn't confirm rather than guessing. State which agent/subagent type and model
you ran as. Write durable findings to .ai/research/<topic-slug>.md (with file
hashes) and any non-code-specific gotcha to .ai/lessons/<topic-slug>.md — update
each INDEX.md. If it's also worth keeping in this plan's own record, append it to
RESULT.md too.
```

**Trust, but verify what matters.** Treat a research worker's findings as reliable
for minor/local facts. For anything the plan critically depends on — a claim that,
if wrong, would derail multiple downstream tasks — spot-check it yourself before
committing to the plan. A wrong implementation usually fails a test; a wrong research
finding just quietly becomes a wrong plan, so it doesn't get the same automatic
safety net. The same caution applies to a cache hit from `.ai/research/` that a
critical decision rests on — a matching hash means the file hasn't changed, not that
the original finding was correct.

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
- this plan's `PLAN.md`, `STATE.md`, `QUESTIONS.md` (under
  `.ai/plans/<plan-slug>/`, per [Project State](#project-state));
- `.ai/research/INDEX.md` and `.ai/lessons/INDEX.md` for anything already known
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
Plan: .ai/plans/<plan-slug>/
Your task: <task ID from PLAN.md>

Before doing anything:
1. Read PLAN.md, STATE.md, and QUESTIONS.md from this plan's folder.
2. Check .ai/research/INDEX.md and .ai/lessons/INDEX.md for anything already known
   relevant to this task.
3. Confirm your assigned task and its acceptance criteria.
4. Inspect the actual code/data yourself.

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
6. If the task produced a reusable investigative finding (code-specific or general),
   write/update it in [Shared Research Cache](#shared-research-cache). If it
   surfaced a durable non-code-specific gotcha, write/update it in
   [Shared Lessons Store](#shared-lessons-store).
7. Return a concise completion report covering: what changed, what was tested, any
   assumptions made, any remaining concerns, and which agent/subagent type and model
   it actually ran as (confirms what was used, in case of a fallback from what the
   orchestrator requested).
8. Report cost — see [Cost Reporting](#cost-reporting) for what's actually available
   to report and how to report it honestly.

This applies equally whether the step was done by a delegated worker or by the
orchestrator working directly on a light plan — whoever did the step updates
`PLAN.md`/`RESULT.md`/the shared stores, not just workers.

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
2. Write the question to this plan's `QUESTIONS.md`: what was discovered, why the plan
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

    [WORKER session=<plan-slug>/<task-id> parent=<parent-session-id>]

- `<plan-slug>`/`<task-id>` — from [Project State](#project-state)/`PLAN.md`.
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
   of its plan's files it touched afterward, the same way the original incident was
   recovered from.
5. **Give each parallel cross-tool worker its own project directory** (`-C <dir>` or
   equivalent, per [Project Isolation](#project-isolation)) — this narrows, though
   doesn't by itself eliminate, the chance of state bleeding between concurrent
   workers sharing one tool's backend.

### In-Process vs Cross-Tool

Communication is entirely file-based, so it doesn't matter to the protocol whether a
worker runs in-process (the orchestrator's own `Agent`/subagent mechanism) or as a
separate cross-tool subprocess (`opencode run`, `codex exec`, `agy -p`) — either way
the worker reads `PLAN.md`/`STATE.md`/`QUESTIONS.md` from its plan's folder and
reports back through the same files. The orchestrator never needs tool-specific
handling once a worker is launched; it just watches for file updates and the return
value like any other worker.

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
be, and it keeps the plan's files a single source of truth with no concurrent
writers.

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
- **Run checks with quiet/concise output**, and keep only pass/fail + errors in plan
  files — never paste raw verbose CI-style output (full test-runner logs, progress
  bars, full lint dumps) into `PLAN.md`/`STATE.md`/`RESULT.md`. If a tool has a
  terser mode (compact test output, a trimmed static-analysis formatter), use it;
  either way, summarize before writing to a plan file.
- **Batch independent steps.** Tool calls whose inputs don't depend on each other's
  output belong in the same turn, not sequential round trips — this applies inside
  plan work exactly as it does everywhere else.
- **`/clear` (or a fresh session) between unrelated phases is safe and encouraged**
  once the current phase's state is actually persisted to the plan folder — that's
  the entire point of resuming cold from files. Don't carry a large, no-longer-needed
  exploration context into an unrelated next phase just because the session happens
  to still be open.
- **Push deterministic checks to scripts/tools that return pass/fail + errors**, not
  narrated tool output — a lint/type-check/test run belongs in `RESULT.md` as "passed"
  or "3 failures: <what>", not as a transcript of the run.

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

A plan is complete only when:

1. All required plan tasks are `done`.
2. Acceptance criteria are satisfied.
3. Tests/checks pass.
4. The orchestrator has independently reviewed the implementation.
5. No known critical blockers remain.
6. The working tree contains only intentional changes.
7. Important limitations are documented.
8. This plan's line in `.ai/plans/INDEX.md` is marked `done`, and — once the user
   confirms it's genuinely finished — the folder is moved per
   [Archiving](#archiving).

The final report summarizes what was built, important architectural decisions, how
it was verified, known limitations, and relevant future improvements. Don't claim
functionality that wasn't actually verified.
