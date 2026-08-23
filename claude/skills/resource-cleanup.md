# Scratch Scripts and Fixed/Reused Resource Paths

Any script — a one-off scratch/dev-server helper, or real project tooling —
that binds to a **fixed, reused** resource path (a Unix socket, a lock
file, a PID file) must find and terminate whatever process is already
holding that resource *before* it unlinks/rebinds it, as the very first
thing it does. Don't rely on a separate "remember to clean up when you're
done" step, manual or otherwise — a session can end abruptly (context
limit, crash, dropped connection, SIGKILL) before any end-of-run cleanup
step ever executes, so a "clean up at the end" habit alone is unreliable
by construction.

Prefer a unique resource path per invocation (timestamp/PID-suffixed) when
that's easy — then there's nothing to orphan in the first place. When a
fixed/reused path is unavoidable or already an established convention, add
the self-cleaning step at start instead.

Found live 2026-08-08 (claude-session-manager): a test/dev-server harness
script only ever unlinked a socket *file* before rebinding, never the
*process* still holding the old listener open — ten orphaned instances had
piled up silently over several days. Matching an AF_UNIX socket back to
its owning process needs `/proc/net/unix` (maps a bound path to the
socket's real kernel inode) cross-referenced against `/proc/*/fd/*` -
**not** `fileinode()`/`stat()` on the socket file, which is a completely
different, unrelated number space and will silently match nothing.
