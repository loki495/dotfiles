---
description: Check context and quota, clean up, then continue here or launch a fresh session for the next step.
disable-model-invocation: true
---

Check this session's context and quota, clean up, then take the next step by the `session-flow` state table: continue here, or launch a fresh session.

**Arguments:** $ARGUMENTS (optional: a plan id, or a short description of the next piece of work when there is no Dibs plan)

---

## 1. Measure

- Context size: the current session's token count (the status line, or the transcript size).
- `sessioneer --usage`: per profile (`personal` is `~/.claude`, `work` is `~/.claude-work`), the `session` and `week_all` percentages and when they reset.
- Pick the plan: the argument, else the plan of a task this session holds a claim on (`todo_claim_status`), else ask. With no Dibs plan, the next step is whatever Andres described or the open items of the conversation.

## 2. Clean up (always, before continuing or launching)

Do these now even if they "should already be done"; report in one line what was already clean.

- **Claims:** complete (`todo_complete` with evidence) or release (`todo_release` with what is left and the exact next step) every claim this session holds.
- **Records:** update the plan body and the finished step (commit SHA, what is next, what blocks it), file follow-ups you noticed, close finished tasks, update the `lesson`/`research` records the work changed.
- **Docs, tests and atlas:** anything the committed work makes wrong is fixed in the repo; touched atlas subsystems updated and stamped with the SHA on master/main.
- **Files:** delete scratch files, temp scripts, `/tmp` outputs, stray state files and temporary branches or worktrees this session created (look at each before deleting; leave anything that is not yours). Backup tags only if the work is confirmed intact.
- **Peers:** `sessioneer --peers`; tell any peer working on the same repo what changed.
- **Nothing pushed without Andres:** if commits are unpushed, say so and ask.

## 3. Ask before assuming

Follow skill `session-flow`, "Questions": collect every question that stops the next step (leftovers of this session and anything the next step's work order leaves open; read it with `todo_next` / `todo_show` first, without claiming) and ask each one with the question tool, recommended answer first, in as many rounds as needed. Do not continue or launch until the answers are in; at the carry quota limit, carry them in the handoff instead.

## 4. Decide where the next step runs

Follow skill `session-flow`: read the state from `thresholds.conf` and the inputs of step 1. GO: continue here (for a plan, `todo_next`, `todo_claim` the step, follow its work order). Anything else: choose the receiver under "Choose the receiver", confirm with Andres what that skill says needs approval, and launch.

## 5. The prompt and the launch

Use "Handoff and prompt" in `session-flow`. Afterwards finish anything still left (answer a peer, record a last checkpoint), clear what this session spawned ("Clear what you spawned"), confirm no claim is held (`todo_claim_status`), and then say plainly, as the last line: **"Safe to archive this session."** If something is still open (a claim, an unanswered question, uncommitted work that is not yours), say what blocks archiving instead.
