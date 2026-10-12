---
description: Per-subsystem maintainability/readability/extensibility audit for the feature-atlas skill family. Given a subsystem's atlas comment (Dibs) or <id>.md (file fallback), re-verifies it against current code and returns ranked, evidence-backed findings (DRY, bugs, schema issues, invalid-state-permitting booleans, duplicated branching, stale-state risks, etc.) in its final response; in file mode it also writes AUDIT-<id>.md. Stays strictly within the subsystem's ownership boundary.
mode: subagent
---

Read `~/dotfiles/ai/agents/feature-atlas-auditor.md` completely and follow it as your instructions for this task. Its frontmatter (`tools:`) is for a different tool — treat everything below it as your operating instructions.
