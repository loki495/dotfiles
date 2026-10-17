# Security

These are personal configuration files, not a deployed service, so there is no supported
release line. Still, if you find a committed secret, or a script that is unsafe to run as
written (for example `install.sh`, `backup-tools/` or `cd-trigger/router.php`), please report
it privately through GitHub's "Report a vulnerability" button on the repository's Security tab
rather than in a public issue.

Secrets and machine-specific infrastructure details are kept out of this repo by design;
they live in a separate private repository that this one only links into place when it exists.
If you spot something here that looks like it should have been private, tell me the same way.
