---
name: verifying-identity
description: Verify identity rather than just success: confirm you are talking to the correct account/environment/tenant, not just that credentials work. Use before declaring credentials or config verified.
---

# Verifying Identity, Not Just Success

A successful, plausible-looking response (a valid API token, real-looking data, a
"200 OK") is not proof you're talking to the *correct* account, environment, or
tenant — only that the credentials/config work for *some* account. This matters most
when there's known history of multiple accounts/environments (old vs. new, staging
vs. prod, a prior attempt at the same integration).

Before declaring credentials/config "verified":

- Where possible, self-verify rather than only asking the user to check manually:
  ask the user for one or more identifying facts you can independently confirm via
  the API (e.g. "what email is on this account?", "how many products are in
  category X?"), then query the API for that same field and compare. If it doesn't
  match, treat the credentials/environment as wrong until proven otherwise — don't
  proceed as if verified.
- If self-verification isn't possible (no distinguishing field available via the
  API), ask the user to confirm independently from a source that can only show the
  true target — their own logged-in dashboard/app — rather than running more API
  calls against the same possibly-wrong credentials.
