# Launching workers, verification, cross-tool

Reference for the `orchestrator-worker` skill; read it when the decision tree in `SKILL.md` points here.

## Launching Workers

**General principle**: launch the worker as an isolated, non-interactive invocation
scoped to the project directory, with a supported explicit fresh-worker model (a full-history
fork inherits its parent model/effort), and a prompt built from
the [worker prompt template](roles-and-workers.md#worker-prompt-template) above. Prefer this over
simulating the worker inline in the orchestrator's own context — the point is to keep
the expensive orchestrator context free of grunt-work tool output, and to run the
worker on a cheaper model.

Three of the four tools converge on the same shape — a headless CLI subprocess that
blocks until done and returns its output:

| Tool | Headless invocation | Model flag | Notes |
|---|---|---|---|
| opencode | `opencode run --model <provider/model> --title "<tag>" "<worker prompt>"` | `--model` | Foreground subprocess; cwd = project dir. `--title` is a real, confirmed flag — always set it to the [worker session tag](launching-workers.md#worker-session-tagging) rather than leaving it to the default truncated-prompt title. Verify exact syntax with `opencode run --help` / `opencode models` — do not invent provider/model names. |
| Codex | `codex exec -m <model> --json "<worker prompt>" < /dev/null` (alias `codex e`) | `-m`/`--model` | Foreground subprocess. **Always redirect stdin from `/dev/null`** — confirmed 2026-08-30: `codex exec` can hang indefinitely waiting on stdin even when a prompt is given as an argument, if stdin isn't a TTY and isn't explicitly closed. `--json` captures real usage, see [Cost Reporting](roles-and-workers.md#cost-reporting). No title/name flag exists — see [Worker Session Tagging](launching-workers.md#worker-session-tagging) for how tagging works without one. See [Background Launch Verification](launching-workers.md#background-launch-verification) before ever backgrounding a codex (or any cross-tool) worker without waiting on it — `codex agents` needs a real TTY and cannot be used from a script. |
| agy (Antigravity) | `agy -p --agent <name> --model <model> "<worker prompt>"` | `--model` | Foreground subprocess (`-p`/`--print` = non-interactive). No title/name flag exists either — see [Worker Session Tagging](launching-workers.md#worker-session-tagging). `--effort` isn't supported on every model. agy has account-wide usage quotas — check headroom before launching several workers in a row. |

Claude Code is the one exception, since the orchestrator is usually already running
inside it: use the `Agent` tool directly rather than shelling out to `claude -p`.
Pick a `subagent_type` (a purpose-built agent, or `general-purpose`), pass the worker
prompt as `prompt`, and use the `model` parameter to pin the cheaper tier — this
override applies only where that tool supports it. Codex full-history forks inherit model/effort
and cannot accept overrides; use fresh/no-history workers for selection. See
[Model Tiering](model-routing.md#model-tiering). Runs synchronously by
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

**Put this as the literal first lines of every worker's prompt** (before the actual
task text), regardless of tool; the first line is `Session name: [worker] <task name>`
(see [message-templates.md](message-templates.md)) and, once it exists, also pass `--name`:

    [WORKER session=<plan-issue-id>/<task-issue-id> parent=<parent-session-id>]

- `<plan-issue-id>`/`<task-issue-id>` — the plan and task issue numbers in Dibs, per
  [Project State](plans-and-state.md#project-state).
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
   task genuinely needs parallelism (see [Parallel vs Sequential Workers](launching-workers.md#parallel-vs-sequential-workers),
   which already defaults to sequential). codex specifically had a confirmed
   concurrent-write race, so treat sequential as firmer still for codex until it's
   been re-tested clean under real parallel load.
2. **Require a real completion sentinel, not just a process-exit signal**, whenever a
   worker does run in the background. `todo_complete` on the task issue *is* the
   sentinel — it's a single durable, structured signal (the issue closes, the claim
   releases) rather than an artificial marker string, and it's exactly the worker's
   own last action per [Worker Completion Protocol](roles-and-workers.md#worker-completion-protocol).
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
   equivalent, per [Project Isolation](plans-and-state.md#project-isolation)) — this narrows, though
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

### Continuation sessions Andres can steer

When the next phase should run as its own session that Andres can watch and answer (a hand-off
to a fresh session, a long-running worker, a follow-up that outlives this context), start it with
`sessioneer` instead of only handing him a paste-ready prompt:
`sessioneer --workdir <dir> --model <model> --effort <level> --mode auto "<prompt that points at the Dibs plan or hand-off>"`
(default `--model sonnet --effort medium` and always `--mode auto` unless Andres asks otherwise),
or `sessioneer --resume <conversation-id> "<message>"` to continue an existing one (it reuses the
live session). It prints the session name; it launches Claude by default and Codex with `--agent codex`; `--effort` works for both (Claude: low to max; Codex: only a level its model lists) while Codex takes no `--profile`, `--no-tools` or `--mode` other than `plan`/`full`, and is host-only. The prompt must be
self-contained like any worker prompt (plan id, file paths, return format), and launching it
counts as a worker launch for the reporting rules below. Bounded workers that return a result
to the orchestrator still use `Agent`; this is for sessions whose output is the human's to steer.

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
`todo:agent:*` CLI via `docker compose -f ~/www/dibs/docker-compose.yml
exec`, which works from any tool regardless of its own MCP support. Confirm which
path a given worker actually has before assuming MCP tool calls will just work —
include the CLI fallback form in its prompt either way, since a cross-tool worker
may not have MCP registered even if the orchestrator does.

**Prioritize the cheapest capable model for every worker, in-process or not** — don't
default to in-process just because it's already open. The in-process/cross-tool
question is purely mechanical (how do I reach the cheapest capable option), not a
reason to skip looking for it. Remember a fork is not part of this comparison at
all — it has no model choice, see [Model Tiering](model-routing.md#model-tiering).

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
[Code Review](practices.md#code-review)). If a cross-tool worker's result is inadequate, that's
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
authority to launch workers per [Blocker Resolution Loop](roles-and-workers.md#blocker-resolution-loop)
and the rest of this protocol. It exists so a wrong or lazy model choice ("used
whatever was already running") is visible in the moment, not discovered later by
asking.

### Parallel vs Sequential Workers

Sequential is the default: one task's result often changes what the next task should
be, not because the old file-based version needed it to avoid concurrent writers —
Dibs's per-issue claims already make that concern structurally moot (see
[Task Claims](plans-and-state.md#task-claims)).

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
