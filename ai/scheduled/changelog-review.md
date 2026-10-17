Scheduled review of the Claude Code changelog (Wednesdays and Saturdays, 12:00). Nobody is watching live; Andres reads the result later.

1. Fetch https://raw.githubusercontent.com/anthropics/claude-code/main/CHANGELOG.md with curl (the GitHub MCP is unreliable). Entries are `## <version>` sections, newest first.
2. Find the last-reviewed version: `todo_search` Dibs for the issue titled "Claude Code changelog review". If it exists, the newest version named in its latest comment is the cutoff. If it does not exist, create it (Personal Projects, Group "AI workflows", label `research`) and treat the first run as a baseline: review only the 10 newest versions.
3. Read only the entries newer than the cutoff. If there are none, add a one-line "no new versions" comment to the issue and stop.
4. Summarize for Andres, in your final message and as a comment on the Dibs issue (start the comment with the newest version reviewed, e.g. `Reviewed through 2.1.302`):
   - Notable new features (skip pure bug fixes and Windows/PowerShell/Bedrock/Vertex-only items unless relevant).
   - Anything that changes how Andres's own setup works: hooks, skills, commands, agents, permissions, settings, MCP, headless/stream-json mode, plugins (his config is in ~/dotfiles/ai, global rules in ~/dotfiles/ai/CLAUDE.md).
5. Check the Sessioneer repo (~/www/personal/sessioneer; read its CLAUDE.md first) against the new entries: new stream-json/headless protocol fields or events, permission modes, hook events, session or transcript format changes, or CLI flags it should support or could now drop a workaround for. For each real opportunity or breakage risk, search Dibs for an existing item, then file a task in the Sessioneer Group with the changelog line, the affected Sessioneer files, and a concrete next step. Do not implement anything and do not edit any repo.
6. Keep the summary short and skimmable. Distinguish what you verified in the Sessioneer code from what is a guess.
