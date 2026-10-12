---
name: claude-import-feature-atlas
description: Discover, document, audit, refresh, or report on a project's feature inventory (Format v2 atlas in Dibs, or .ai/feature-atlas/ when Dibs is unreachable).
---

Read the requested maintained workflow completely: `commands/feature-atlas.md`, `commands/feature-atlas-subsystem.md`, or `commands/feature-atlas-report.md` under `~/dotfiles/ai/`. When a specialized phase is needed, read the matching `feature-atlas-*.md` under `~/dotfiles/ai/agents/`. The atlas lives in Dibs (parent issue labelled `research` and `feature atlas`, one comment per subsystem) when the `dibs` MCP or `todo:agent:*` CLI is reachable, and under `.ai/feature-atlas/` otherwise. Everything runs in the foreground; delegation is optional unless the user explicitly requests it.
