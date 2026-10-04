---
topic: cloudflare-ssl-one-subdomain-level
tags: [cloudflare, ssl, dns, subdomains, general]
---

Cloudflare's free Universal SSL certificate covers the apex domain and one level of
subdomains (`example.com`, `*.example.com`) — not deeper ones. A proxied hostname like
`vite.app.example.com` or `demo.project.example.com` gets a TLS handshake failure at
Cloudflare's edge even though DNS resolves fine, which looks like a server or Traefik
problem but isn't.

When naming proxied hostnames, flatten them to one level (`app-vite.example.com`,
`project-demo.example.com`) rather than nesting. The alternatives — an Advanced
Certificate (paid) or unproxied (grey-cloud) DNS with your own certificate — are only
worth it when the nested name is truly needed.

Hit in practice when per-project dev/demo subdomains (Vite dev server, demo sites)
were nested under a project subdomain; the fix was renaming them to a single level.
