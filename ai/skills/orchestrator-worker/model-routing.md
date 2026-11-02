# Model tiering and routing by work type

Reference for the `orchestrator-worker` skill; read it when the decision tree in `SKILL.md` points here.

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
  [In-Process vs Cross-Tool](launching-workers.md#in-process-vs-cross-tool) for how to compare across
  tools without making the comparison itself expensive.

**A fork is not a lever for model cost.** A fork always runs on the orchestrating
session's own model — a `model` override passed to a fork is ignored. Forking saves
tokens a different way: it inherits full context and shares the prompt cache, so
there's no cold-start re-derivation the way a fresh agent has. Choose between a fork
and a fresh/cross-tool worker based on which cost actually dominates for the task at
hand — context re-derivation (fork wins) or per-token price (a cheaper fresh
worker wins) — not out of habit. See also
[Research Delegation](plans-and-state.md#research-delegation) for this same tradeoff applied to
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
[escalation criteria](plans-and-state.md#when-this-applies) above.

Bump a worker to a stronger model only when the bounded task itself genuinely
requires deep reasoning (diagnosing a subtle bug, reconciling conflicting
constraints) — not by default "to be safe," and not just because it's the model
already running. Whichever model gets picked, state *why* — "cheapest capable option
available" is a real justification, but it has to have actually been checked against
the alternatives, not assumed. Record the exact worker model, which tool it ran in,
and that justification as a `todo_comment` on the plan issue. Don't assume a model's cost or availability
from its name; verify with the tool's own model listing before launching
(`opencode models`, `codex debug` / `-c model=...` docs, `agy models`, etc.).

### Model routing by work type

The canonical list for picking agent, model and reasoning effort; general sessions, workers and
`sessioneer --agent/--model` all use it. Pick the tier from the work, then take the
highest-ranked entry whose agent is installed, has quota, and lists the model. Entries are
`agent model, effort`. Effort is named even where a tool has no flag: `sessioneer --effort <level>` sets it on a
Claude launch (low, medium, high, xhigh, max; fixed at spawn) and a Codex launch (a level the model
lists; needs a prompt), other agents take it via their own setting or the prompt.
Temperature is left at each tool's default.

**mechanical**: read/search, renames, formatting, running lint/tests, bulk edits with a clear spec.
1. opencode `opencode/deepseek-v4.1-flash-free` (saves Claude and Codex quota for planning and important work)
2. codex `gpt-6-luna`, low
3. claude `claude-haiku-5-5`, low
4. opencode `opencode-go/claude-haiku-5-5`, low
5. agy `gemini-3.8-flash-low`

**balanced**: the default; implementing a decided plan step, diff review, docs, discussion.
1. claude `claude-sonnet-5-5`, medium
2. codex `gpt-6.1-terra`, medium
3. opencode `openai/gpt-6.1-terra`, medium
4. agy `gemini-3.8-flash-high`
5. agy `claude-sonnet-4-6`

**advanced**: planning, architecture, audit design, subtle debugging, multi-file refactors with design choices.
1. codex `gpt-6.1-sol`, high
2. claude `claude-opus-5-5`, high
3. opencode `openai/gpt-6.1-sol`, high
4. agy `claude-opus-4-6-thinking`

**frontier**: the hardest problems only (races, security-critical design, a stuck advanced attempt).
1. codex `gpt-6-astra`, max
2. claude `claude-fable-5-1`, max
3. claude `claude-opus-5-5`, max

- **Choosing**: rank 1 is the preferred model for the tier; lower ranks are fallbacks for no
  quota (see Quota awareness), a missing install or a model missing from the tool's listing. A
  fallback keeps the tier's listed effort. If the list runs out, move *up* one tier, never down
  for advanced or frontier work.
- **Launching without a prompt**: mechanical sessions and workers (the list above) are launched
  as needed without asking Andres, with the agent, model and reason stated. Planning, advanced
  work and any larger or longer session still need his go-ahead before launching.
- **Coordinate**: sessions talk to each other. When you see changes, claims or branches that are
  not yours, run `sessioneer --peers` and `--send` the owner to split or sequence the work
  (skill `peer-sessions`) rather than editing around them silently.
- **Frontier needs Andres's approval first**, plus a `sessioneer --usage` check. Advanced is the
  ceiling for an autonomous choice. Start at the listed effort; raise it (low, medium, high,
  xhigh, max) before raising the tier when the model is right but sloppy.
- **Verify before launching**: names come from each tool's own listing (`codex debug models`,
  `opencode models`, `agy models`) as of 2026-10-26, and the luna < terra < sol ordering is
  inferred from the names. Re-check when a listing changes and edit this list, not the rule that
  points here.
- State the tier, model, effort and reason as the worker launch reporting format requires and
  record them in the plan comment.

### Cost gates and lightweight workers

Decided 2026-10-07 from a 7-day transcript audit (the full numbers and the model-by-phase
rule are in `CLAUDE.md`, "Model choice, turns, and delegation cost"): a worker's cold
start (this skill is ~15k tokens, plus the plan, task, and research/lesson lookups) and
four-plus Dibs calls per task cost more than they save on a small task, and in-process
workers were inheriting the orchestrator's Opus model.

- Delegate when the work would put roughly 10k+ tokens of tool output in the orchestrator's
  context, not because it is "multi-step". Do 3 or fewer calls inline.
- Pass `model` explicitly on every `Agent` launch; never rely on inheritance.
- **Lightweight worker** (the default for bounded in-process tasks): a self-contained
  prompt of about 400 words (goal, absolute paths, acceptance criteria, what to return in
  300 words or less). It skips this protocol, the claim/heartbeat/complete cycle, and
  the research/lesson lookups. The orchestrator checks the research cache before
  launching, reviews the result, and records the phase in one `todo_comment` and one
  `todo_complete` per task. Use the full worker template below only for long-running,
  cross-tool, or parallel workers where a live claim is what prevents a collision.
- The orchestrator session is short-lived: plan and dispatch, then hand off. Review of
  the result happens from the diff, in a fresh session if the orchestrator's context is
  large.

The orchestration protocol itself must not depend on a particular model's identity —
the same project should be able to swap worker models later (a free tier, a stronger
coding model, a different provider) without changing anything else.
