---
name: claude-import-orchestrator-worker
description: Split expensive planning/review reasoning from cheap bounded execution using an orchestrator (plans, delegates, reviews) and workers (each execute one bounded task, communicating via .ai/PLAN.md, STATE.md, QUESTIONS.md, RESULT.md). Use for any task complex enough to warrant explicit planning plus delegated implementation.
---

Read `~/dotfiles/ai/skills/orchestrator-worker/SKILL.md` completely before acting as either an orchestrator or a worker in this protocol. When launching a worker as a separate Codex session, use `codex exec -m <model> "<worker prompt>"` per that file's Launching Workers section — verify exact flags with `codex exec --help` first.
