---
description: Decide with `sessioneer --next`, clean up, ask, then continue here, hand off and rotate to a fresh session, park or wait.
disable-model-invocation: true
---

Take the next step by the `session-flow` state table: `sessioneer --next` decides, and this command cleans up, asks, then continues here or hands off and starts a fresh receiver session with `sessioneer --rotate`. A session that ended or died without a handoff is `/takeover`'s path instead.

**Arguments:** $ARGUMENTS (optional: a plan id, a handoff id, or a short description of the next piece of work when there is no Dibs plan)

---

## 1. Decide

Run `sessioneer --next --json`. Add the target session (`sessioneer --next <name> --json`) when this session is not the one deciding, and `--plan <id>`, `--handoff <id>` or `--intent step-end|wait|done` when the next step is already known.

Read `state` (`GO`, `WARM_TIGHT`, `CHECKPOINT`, `ROTATE`, `PARK`, `WAIT`, `DONE` or `UNKNOWN`), `why`, `trigger`, `receiver`, `reset_at`, `prompt_kind`, `needs_approval` and `warnings`, and follow skill `session-flow`'s state table. The numbers live only in its `thresholds.conf`. Say the decision in two lines before acting.

When the binary is missing or the call fails, measure context and run `sessioneer --usage` yourself, read the state from `thresholds.conf`, and say in the reply that you fell back.

## 2. Clean up (always, before continuing or launching)

Run skill `session-flow`, "Clean up before leaving", and report in one line what was already clean.

## 3. Ask before assuming

Follow skill `session-flow`, "Questions": collect every question that stops the next step (leftovers of this session and anything the next step's work order leaves open; read it with `todo_next` / `todo_show` first, without claiming) and ask each one with the question tool, recommended answer first, in as many rounds as needed. Do not continue or launch until the answers are in; at the carry quota limit, carry them in the handoff instead.

## 4. Act on the state

- **GO:** continue here. For a plan, `todo_next`, `todo_claim` the step it returns, and follow its work order.
- **WARM_TIGHT / CHECKPOINT:** finish the current step, write the checkpoint, update the plan and records, and release claims. Start no large step.
- **ROTATE:** file the handoff with skill `session-handoff` unless a plan step's work order already carries everything the receiver needs, then launch under "Launch and finish" with the receiver the decision names or your own choice from `session-flow` "Choose the receiver". Add `--dry-run` first when the prompt matters. Report the receiver's name, finish what is left here, and leave this session running: the receiver archives it.
- **PARK:** file the handoff, release claims, and say when quota resets.
- **WAIT:** the status line only; the claim may stay.
- **DONE:** closer checks, clear what this session spawned, then the status line.

## 5. Offer path

With no hook, or when Andres would rather tap than wait for a launch, post the rotation with `sessioneer --offer` as `session-flow`, "Handoff and prompt", describes, and check the session's live offer first so you do not duplicate one.

## 6. Launch and finish

Launch with the `sessioneer --rotate` forms, shaping options, refusals and source naming in `session-flow`, "Handoff and prompt". Tell Andres the receiver's name, agent, model, effort, profile and workdir, and that it archives this session once it has claimed the work ("Archive a replaced session"). If the launch is refused, say why and leave the session as it is. Nothing is pushed as part of a rotate.

Afterwards finish anything still left (answer a peer, record a last checkpoint), clear what this session spawned ("Clear what you spawned"), and confirm no claim is held (`todo_claim_status`). After a rotate the last line is **"Waiting on other work: the receiver <name> takes over and archives this session."** When you continued here instead, say **"Safe to archive this session."** only once nothing is held; if something is still open (a claim, an unanswered question, uncommitted work that is not yours), say what blocks archiving instead.
