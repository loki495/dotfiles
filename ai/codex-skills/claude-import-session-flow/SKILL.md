---
name: claude-import-session-flow
description: The one state machine for continuing, parking, rotating and cleaning up sessions, with the thresholds file, receiver choice, questions and spawned-session cleanup.
---

Read `~/dotfiles/ai/skills/session-flow/SKILL.md` and `thresholds.conf` in that directory completely at every step boundary, near quota or a big context, before launching or replacing a session, and before a final status line. Use your own question tool for every question and every proposal to continue in a new session. Never launch a session, push or do a real-world action without Andres's approval where the skill says so.
