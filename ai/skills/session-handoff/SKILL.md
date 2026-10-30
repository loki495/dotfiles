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

- Near quota (rule 747): write it **before** the session can no longer run tools. A session cut
  off mid-turn cannot write anything, so this is a 90%-time job, not an end-of-session one.
- Waiting on Andres: a decision, a real-world action, a check only he can do.
- Blocked on another session's claim, a PR, a deploy or a review.
- Ending with anything uncommitted, untested, unmerged, or undocumented.

The session releases its claims (rule 728) and files the handoff. The handoff task is what the
receiver claims, not the abandoned task.

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
    Why parked: quota <session/week %> | decision needed | real-world action | blocked by <what> | done, verify
    State: committed <sha>; uncommitted <paths>; untested <what>
    Changed since the plan: <the delta a cold session needs — a decision just made, a dead end, a constraint found>
    Next steps: <ordered, copy-pasteable commands, the very next action first>
    Needs Andres: <the one thing only he can do> — or "nothing, any agent can continue"
    Open questions: <unresolved or unconfirmed>
    Don't: <tried and ruled out, or things Andres said not to pursue, so the next session does not retry them>
    Cleanup: <temp branches/worktrees, background processes, containers, serve restarts>
    Docs/atlas: <what is still stale, and where>
    Resume: sessioneer --agent <agent> --resume <id> "..." — or "any agent can continue from this task"

In Claude Code, `/handoff` runs this procedure and prints the paste-ready prompt for the next
session; the fields above are the ones it fills in.

**The handoff is a delta, not a summary.** The plan is the durable record of why the work exists;
the handoff carries what changed since the plan was last read and what a cold session must know
before touching anything. If it repeats the plan, link to the plan instead.

**Durable knowledge never lives only here**, because this task is deleted on completion. A real
lesson, a changed requirement, a decision or a design conclusion goes to the plan, or to a
`lesson` / `decision` / `research` record, *before* the handoff is filed. The handoff may point at
it; it may not be the only copy.

## Receiving one

1. Find it: `todo_list label=handoff state=OPEN` — every parked session, all agents, one screen.
2. Claim it. That is the lock; two sessions must not both act on the same handoff.
3. Do the work. The body is meant to be self-sufficient; resume the parked session only if the
   work genuinely needs its transcript.
4. Fold anything durable into the plan or a knowledge record first.
5. `todo_complete` — the task is deleted. A completion summary is copied to the permanent parent
   as a normal comment, so keep it public-safe or omit it. A handoff whose plan moved on is
   discarded with `NOT_PLANNED`, which also deletes it.

Older than about a week: verify before acting. The repo, the branch or the decision may have
moved on, and the plan is the authority, not the handoff.

## Not this

- Not a plan replacement, and not a place for durable findings.
- Not a file: no hand-off markdown in the repo, nothing to delete later.
- Not a claim: the parked session's claim is released, and the receiver's claim is on this task.
