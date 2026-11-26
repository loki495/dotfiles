---
name: claude-import-takeover
description: Continue another Sessioneer session's unfinished work after reading its complete conversation and Dibs state; Sessioneer archives the source once it is idle and claim-free.
---

Read `~/dotfiles/ai/skills/takeover/SKILL.md` completely and follow it. Input is `<source agent> [Claude profile] <conversation id>`. Run `sessioneer --replaces <conversation id>` before anything else so Sessioneer archives the source once it is idle and claim-free; do not archive it by hand, and never force-stop a working or blocked session.
