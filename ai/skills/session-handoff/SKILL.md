---
name: session-handoff
description: How to park unfinished work so a cold session can pick it up hours or days later — one temporary Dibs task per parked session, labelled `handoff`, parented to its plan step, with a fixed body (state, next steps, what Andres must do, cleanup, docs/atlas). Use when a session stops with work unfinished: near quota, waiting on a decision or a real-world action, blocked, or ending before the work is done.
---

# Session handoff

A session that stops mid-work leaves three things behind: a claim, a half-finished step and a
reason. The reason is the part that gets lost, and it is the only part a cold session cannot
reconstruct.

The handoff is one **temporary Dibs task** per parked session. It is local-only, never mirrored
to GitHub, and hard-deleted when the receiver completes it, so nothing accumulates and nothing
needs cleaning up. No files on disk.

## When to write one

- Near quota (rule 728): write it **before** the session can no longer run tools. A session cut
  off mid-turn cannot write anything, so this is a 90%-time job, not an end-of-session one.
- Parking while waiting on Andres: a decision, real-world action or check only he can do.
- Parking while blocked on another session's claim, PR, deploy or review.
- Ending with anything uncommitted, untested, unmerged, or undocumented.

Continue-in-this-session and both Waiting statuses may retain/renew claims while this same
session will act again; they do not themselves park/transfer work. When parking or transferring,
file the handoff first, give Andres its id, then release claims with exact next steps. The handoff
is what the receiver claims, not the abandoned task. Read `orchestrator-worker/work-tracking.md`
for final-status, quota, recovery and no-hook MCP/CLI checks.

## Create it

    todo_create temporary: true
      title:   Handoff: <what is left> — <agent>:<session name>
      labels:  handoff  (+ waiting | decision needed | needs manual verification)
      parent:  the plan step or permanent task it belongs to, when there is one

One per parked session. Not one per todo item, and not a shared inbox: two sessions can park on
the same plan, each with its own workdir and branch, and a shared task turns into claim
contention. A temporary child does not stop a permanent step counting as a leaf, so it never
blocks `todo_next`.

Give Andres the id in your last message. He does not need it to find the work (see below), but it
is the shortest path back.

## The body

    Session: <agent> · <session/conversation id> · <workdir> · <branch>
    Goal: <what we are trying to achieve, one or two sentences>
    Decisions made: <answers Andres already gave and choices settled, so the receiver does not ask again>
    Why parked: quota <session/week %> | decision needed | real-world action | blocked by <what> | done, verify
    State: committed <sha>; uncommitted <paths>; untested <what> (the receiver re-verifies it with git, tests and Dibs)
    Changed since the plan: <the delta a cold session needs — a decision just made, a dead end, a constraint found>
    Next steps: <ordered, copy-pasteable commands, the very next action first>
    Needs Andres: <the one thing only he can do> — or "nothing, any agent can continue"
    Open questions: <unresolved or unconfirmed; the receiver asks these with the question tool>
    Don't: <tried and ruled out, or things Andres said not to pursue, so the next session does not retry them>
    Cleanup: <temp branches/worktrees, background processes, containers, serve restarts>
    Docs/atlas: <what is still stale, and where>
    Resume: sessioneer --agent <agent> --resume <id> "..." — or "any agent can continue from this task"

In Claude Code, `/rotate` files this handoff and starts the receiver; the receiver choice, the prompt shapes and when to ask versus carry questions are in skill `session-flow`. A small job with nothing to carry gets a short self-contained prompt instead of a Dibs task.

After filing it, recommend the receiver (agent, model, effort, profile, workdir) and prompt shape as `session-flow` describes, then ask with the question tool, recommended option first: start it now with that choice, start it with another agent or model Andres names, or only print the prompt. Never launch without the answer. Reply with the task's local id and a paste-ready prompt: "Read and claim temporary task `<id>`, continue from Next steps, and complete it after consumption; ask about unresolved Open questions."

**The handoff is a delta, not a summary.** The plan is the durable record of why the work exists;
the handoff carries what changed since the plan was last read and what a cold session must know
before touching anything. If it repeats the plan, link to the plan instead.

**Durable knowledge never lives only here**, because this task is deleted on completion. A real
lesson, a changed requirement, a decision or a design conclusion goes to the plan, or to a
`lesson` / `decision` / `research` record, *before* the handoff is filed. The handoff may point at
it; it may not be the only copy.

## Receiving one

1. Find it: `todo_list label=handoff state=OPEN` — every parked session, all agents, one screen.
2. Claim it. That is the lock; two sessions must not both act on the same handoff. Once it is
   claimed, archive the source session by `session-flow`, "Archive a replaced session".
3. Do the work. The body is meant to be self-sufficient; resume the parked session only if the
   work genuinely needs its transcript.
4. Fold anything durable into the plan or a knowledge record first.
5. `todo_complete` after consuming any temporary children — the task is deleted, with no undo. A
   completion summary is copied to the permanent parent as a normal comment and follows that
   parent's mirroring policy, so keep it public-safe or omit it. A handoff whose plan moved on is
   discarded with `NOT_PLANNED`, which also deletes it. A normal `todo_release` keeps it for another
   session.

Older than about a week: verify before acting. The repo, the branch or the decision may have
moved on, and the plan is the authority, not the handoff.

## Not this

- Not a plan replacement, and not a place for durable findings.
- Not a file: no hand-off markdown in the repo, nothing to delete later. Only when Dibs is
  unreachable, or Andres names a file, use a private scratch file outside any repository and say where
  it is. Never put tokens or secrets in either form.
- Not counted: temporary records stay out of durable plan and atlas accounting and out of reconciler
  evidence checks.
- Not a claim: the parked session's claim is released, and the receiver's claim is on this task.
