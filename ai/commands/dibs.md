File a task in Dibs from a free-text prompt.

**Arguments:** $ARGUMENTS

The argument is what to add (a task, bug, follow-up or idea), in the user's own words. Do not implement it; only file it.

**Steps:**

1. If the argument is empty, ask what to add and stop.
2. Orient with the `dibs` MCP server (`todo_context`, `todo_metadata`, and `todo_search` for the topic and for likely duplicates). If MCP is unreachable, say so and use the `todo:agent:*` CLI fallback from the `orchestrator-worker` skill (Project State section); never write to the DB directly.
3. Work out from the prompt, the current repo/path, and that metadata:
   - **Project area** (Work, Personal Projects, Learning & Self-Improvement, Random Tasks)
   - **Group** (one per project/website/topic; reuse an existing one, create by name only if none fits)
   - **Parent issue** (the project's parent issue; if the project has none yet, create a lightweight one with repo path, stack and purpose)
   - **Labels** (existing ones, spaces not hyphens; `bug` for bugs; `plan` only for genuinely multi-step work)
   - **Title and body**: the user's intent in their own words, plus relevant files/paths and context from the prompt.
4. If a duplicate or near-duplicate open item exists, update it (`todo_comment` or `todo_revise`) instead of creating a new one, and say so.
5. Ask the user, in one batched message with a recommended default for each, only about:
   - **Ambiguity about what they mean** (what the task actually is or wants), and
   - **Area/group/parent/labels you could not determine** with reasonable confidence.
   Skip the question round entirely when everything is clear.
6. Other ambiguities (design choices, scope details, anything that can wait for whoever does the work) are not asked now. List them in the task body under an **Open questions** heading, marked to be asked when the task is claimed and worked on.
7. `todo_create` the task. Reply with the id, title, area/group/parent/labels, and any open questions recorded. Then continue whatever you were doing; do not start the task unless told to.
