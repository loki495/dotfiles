Run a whole Dibs plan (from any agent; each worker's agent is chosen by tier and remaining quota): launch a worker session per task (right agent, model, effort), in parallel where tasks don't block each other, verify each one's evidence against its done requirements, send it back until it is really done, archive it, and loop until the plan is finished. `/next` does one task; this does the plan.

**Arguments:** $ARGUMENTS (a plan id; with none, the plan of a task this session holds a claim on, else ask)

---

## 1. Read the plan and check there is room

- `todo_show` the plan and every open child (`todo_list`, batch `todo_show`). Note for each task: its work order, `tier`, `repos`, dependencies/blockers, `decision needed` flags, and its **done requirements** (acceptance criteria, tests, docs, atlas, evidence expected). A task with no stated done requirements: derive them from the rules (docs and tests with the change, atlas stamp, closed tasks) and write them into the task before launching.
- Measure like `/next` step 1: context size and `sessioneer --usage` for every agent and profile.
- **Context too big** (over about 150k, or already past the orchestrator limit): do not start the loop here. Clean up as `/next` step 2 (claims, records, nothing pushed), then launch a new orchestrator: `sessioneer --workdir <dir> --agent <a> --model <m> --effort <e> --mode auto "/orchestrate <id>. Answers already given: <decisions>"`, picked from the **advanced** tier of the model-routing list (orchestrating means judging evidence); confirm with Andres first if that is frontier. End with **"Safe to archive this session."** only once nothing is held.
- **Quota too tight** (every agent that could run the work is at 90% or more of `session` or `week_all`): stop, say when it resets, do not launch.

## 2. Ask before assuming (once, up front)

Collect every open question across the whole plan: `decision needed` tasks, ambiguous repos or branches, pushes, anything frontier-tier. Ask every one with the question tool (Claude: AskUserQuestion; Codex: its user-input tool, else a numbered list at the end of the reply), one explanation each, recommended option first. There is no limit on questions per batch or on batches: if the tool caps a call, make several and repeat until nothing is left to assume. Workers are told not to ask Andres anything the plan already answers, so decide here.

## 3. Schedule

Build the dependency graph from the plan (explicit blockers, plus implicit ones: two tasks editing the same files, same repo checkout, a migration or shared config one of them changes, a task that consumes another's output). A task is **ready** when everything it depends on is verified done. Launch the ready set in parallel only when they:

- touch disjoint files (give each its own worktree if they share a repo and could overlap; the live-deployment rule still applies),
- don't compete for the same live claim, container, port or database,
- fit the quota (cap concurrent workers at 3 unless Andres says otherwise).

Otherwise serialize. Say the graph and the first wave in a few lines before launching.

## 4. Launch each worker

Per task pick **agent, model, effort** from the tier table in the `orchestrator-worker` skill ("Model routing by work type"): the task's `tier` if set, else by work type. Highest-ranked entry that is installed, lists the model and has quota left in `sessioneer --usage` (re-read it before each wave; skip an agent or profile at 90% or more), regardless of which agent this session is. Frontier only with Andres's approval. Name agent, model, effort and reason before launching.

`sessioneer --workdir <repo or worktree> --agent <a> --model <m> --effort <e> --mode auto [--profile <p>] "<prompt>"`

Prompt (small, self-contained):
`You are a worker for plan <id>. Claim task <tid> (agentName <agent>:<session name>:<conversation id>) and follow its work order. Done means every done requirement in the task is met, with evidence in a todo_comment: commit SHA, test command and its output, doc/atlas changes. Do not push. Do not ask Andres anything the task does not leave open; message the orchestrator (<my session name>) with sessioneer --send for blockers. When finished, complete the task with that evidence and release the claim. <decisions from step 2 that apply>.`

Wait without polling: run each launch's completion in the background (`sessioneer --wait --timeout 3600 ...` as a background Bash command, which re-invokes you when the worker goes idle), or answer peer messages as they arrive. A worker that is `blocked` on a prompt only Andres can answer: tell him which session and why.

## 5. Verify, never trust the report

When a worker reports done, check it yourself against the task's done requirements, cheaply (read-only):

- `todo_show` the task: evidence comment present, status, claim released.
- The commit exists and touches what the task said (`git log`, `git show --stat`); diff matches the work order, nothing out of scope.
- Re-run the stated tests or checks, or at least the one that proves the claim; docs, atlas and follow-up tasks updated as required.
- Anything the worker said it could not do is recorded, not silently dropped.

**Not met:** `sessioneer --resume <conversation id> "Not done: <each unmet requirement, what you checked, what is expected>. Finish it and report evidence."` and wait again. Repeat until verified. If a worker fails the same requirement twice, raise effort, then tier (not frontier without Andres), or take it over; if still stuck, release it, file the blocker in Dibs and tell Andres.

**Met:** make sure its claim is released and the task closed with the evidence, then archive the session: `sessioneer --kill <name>` (refuses a working one; stopped conversations stay resumable). Update the plan body (task done, SHA, what unblocked), recompute the ready set and launch the next wave. Back to step 4.

## 6. Finish

When every task is verified done, or the rest are blocked on Andres: check the plan's own done requirements (docs, atlas, closed tasks, leftover worktrees and branches this run created), complete or update the plan in Dibs, release your claims (`todo_claim_status`), and report: tasks done with SHAs, anything blocked and why, unpushed commits (ask before pushing, naming remote and branch), quota used. Last line **"Safe to archive this session."** only if nothing is held or open; otherwise say what blocks it.

Keep Dibs current as you go: if this session dies mid-run, a fresh `/orchestrate <id>` must be able to resume from the plan, the task states and the live `sessioneer --list` alone.
