Write a hand-off file so a fresh session can continue this work cold, then give a ready-to-paste prompt that points to it.

**Arguments:** $ARGUMENTS (optional: where to write it, or what to focus on)

---

**Where:** if the work has a Dibs plan issue, update that plan instead of writing a file (see the `orchestrator-worker` skill). Otherwise write `.claude/handoff-<topic>-<YYYY-MM-DD>.md` in the project, or wherever the arguments say. Never put tokens or secrets in it. Infrastructure details go in the private dotfiles, not in a public repo.

**What goes in it:** the current state only. Don't narrate earlier states or approaches that were dropped.

- **Goal:** what we're trying to achieve, in a sentence or two.
- **Current state:** what works now, what's committed (branch and last commit), and what's uncommitted.
- **Decisions agreed:** each decision Andres made this session, stated as a fact.
- **Confirmed lessons:** only things verified for sure (gotchas, hardware facts, commands that work), each marked as verified. Anything still uncertain goes under Open questions, not here.
- **Environment:** the hosts, containers, paths, devices and commands needed to resume.
- **Next steps:** an ordered list, with the very next action first.
- **Open questions:** anything unresolved or unconfirmed.
- **Don't:** things that were tried and ruled out, or that Andres said not to pursue, so the next session doesn't retry them.

Then reply with the file path (or Dibs issue) and a short paste-ready prompt, e.g. "Read `<path>` and continue from Next steps; ask before anything listed under Open questions." Durable, general lessons also belong in a `lesson`-labeled Dibs issue or `~/.claude/lessons/`. Offer to file them.
