---
name: orchestrator-worker
description: Protocol for multi-step or multi-session work with a Dibs plan, workers and model tiering. Use when planning, delegating to workers, resuming a plan or choosing a model tier; not for single-turn edits.
---

# Orchestrator/Worker Protocol

Tool-agnostic: Claude Code, opencode, Codex and agy can each be orchestrator or worker. This is the
default way multi-step work happens, not something to invoke on request. Hard rules live in Dibs
rules (injected by the rule-inject hook; other agents grep `ai/rules.md`): claim before working
[727], complete or hand off before leaving [728], keep Dibs current/lean/readable [729], finish code/tests/docs/records [730],
ranked model routing and delegation [926], filing [927], independent personas [1468].

The loop: investigate, plan, delegate if warranted (cheapest capable model, one bounded task per
worker), workers complete or block and ask, the orchestrator answers or re-plans, then review,
verify, complete. The orchestrator optimizes for correctness; a worker may stop and ask and the
orchestrator listens.

## Decision tree

Before claims, Dibs bookkeeping or session disposition, read `work-tracking.md` completely.

1. **Size the request** (small: do it; medium: one batched question round and a short draft; large:
   Dibs plan with a running draft) → `plans-and-state.md`, "Sizing a request".
2. **Does it need a plan?** Yes if explicitly multi-phase, an audit, framed as a todo list, or it
   will span sessions. No for single-turn, single-file work (plain reply or in-session todo list).
   Unsure: create the plan (one `todo_scaffold_plan` call). → `plans-and-state.md`, "When This
   Applies", "Planning", "Project State" (plan body, checkpoints, claims, completion).
3. **Before researching anything:** search Dibs `research` and `lesson` records; update them after.
   → `plans-and-state.md`, "Shared Research Cache", "Shared Lessons Store", "Research Delegation".
4. **Split the work** into bounded tasks with Done-when/Evidence/Files likely →
   `plans-and-state.md`, "Task Decomposition".
5. **Delegate?** Only when the footprint is large, subtasks are independent, or a cheaper model
   plausibly handles a bounded piece. Clear case: do it; ambiguous: one quick check-in; never
   silently. Solo work that clears the plan bar usually stays solo.
   - Pick agent, model and effort by work type → `model-routing.md` (tier table, cost gates).
   - Write the worker prompt and handle completion, cost reporting, questions and blockers →
     `roles-and-workers.md`.
   - Substantial feature, bugfix or refactor: rule 1468 requires choosing and recording the persona
     profile before implementation. Use independent contexts for the required roles, not role
     labels in one conversation. Split it across personas (designer, test builder, implementer, runner,
     interpreter, reviewer, closer) → `personas.md` (matrix, prompts, profiles, test ownership).
   - Launch, tag, verify the launch, cross-tool or continuation sessions, parallel vs sequential →
     `launching-workers.md`.
   - Prompt, result, peer-message and Dibs-block shapes, session naming and the `[worker]` tag →
     `message-templates.md`.
6. **You are a worker:** read `roles-and-workers.md` ("Role: Worker", completion protocol); claim
   your task, stay in scope, ask rather than guess, report cost and evidence.
7. **Finishing:** review, tests, docs, atlas, closed tasks, claims released →
   `practices.md` ("Final Completion", "Code Review", "Testing", "Git", "Privacy", "Scope Control").
   Token-saving habits → `practices.md`, "Token Efficiency Practices".

## Always

- Plans live in Dibs only, never local plan files; the plan body is the maintained document,
  comments hold concise evidence, one living checkpoint per claim.
- Quota: check `sessioneer --usage` before long work; at about 90% park the work with a handoff
  (skill `session-handoff`).
- Reads of Dibs records: `todo_show` returns 1500 characters of body by default; batch with `ids`.
