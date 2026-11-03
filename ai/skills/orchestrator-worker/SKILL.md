---
name: orchestrator-worker
description: Default protocol for multi-step coding work, solo, forked or delegated to workers. A plan is a `plan`-labeled issue in Dibs (MCP server `dibs`; `todo:agent:*` CLI fallback) so any session of any agent can resume it cold; research and lessons are shared Dibs records; small work escalates to workers and model tiering only when warranted. Use by default for multi-step work, not only when asked.
---

# Orchestrator/Worker Protocol

Tool-agnostic: Claude Code, opencode, Codex and agy can each be orchestrator or worker. This is the
default way multi-step work happens, not something to invoke on request. Hard rules live in Dibs
rules (injected by the rule-inject hook; other agents grep `ai/rules.md`): claim before working
[727], never end holding a claim [728], keep plans current [729], done means all of it [730],
name agent and model before launching and delegation cost [926], quota [747], keep Dibs lean [757], filing [927],
model tiers [1067].

The loop: investigate, plan, delegate if warranted (cheapest capable model, one bounded task per
worker), workers complete or block and ask, the orchestrator answers or re-plans, then review,
verify, complete. The orchestrator optimizes for correctness; a worker may stop and ask and the
orchestrator listens.

## Decision tree

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
   - Launch, tag, verify the launch, cross-tool or continuation sessions, parallel vs sequential →
     `launching-workers.md`.
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
