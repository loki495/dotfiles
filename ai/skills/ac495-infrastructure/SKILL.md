---
name: ac495-infrastructure
description: How Andres's home lab is wired together under the example.com domain — Traefik routing, Pi-hole split-horizon DNS, the Cloudflare Tunnel/Access setup, and which of the two LAN machines hosts what. Use before adding a new *.example.com service, debugging why a service is unreachable (especially from inside a Docker container), or touching anything under ~/www/traefik.
---

# example.com home lab

Confirmed directly from `~/www/traefik/` config and this machine's own network/SSH
config on 2026-08-29 — re-verify anything load-bearing if it's been a while, this is
a personal home-lab setup that changes as things get added.

## The machines

- **`work`** (`10.10.0.10`) — **this machine.** Docker host for Traefik itself and
  every `@docker`-routed app (homie, csm, git, adminer, the various client
  projects, claude-ui, etc. — see `~/www/traefik/dynamic/ac495-sites.yml`'s first
  block of routers).
- **`media`** (`10.10.0.20`, SSH alias `media`) — the media box. Hosts Pi-hole, the
  Cloudflare Tunnel (`cloudflared`), and the *arr stack (Sonarr/Radarr/Prowlarr/
  Jackett/Nzbget/Bazarr/qBittorrent), plus HomeAssistant, ESPHome, a status page, a
  stocks app, and LazyDocker. These aren't on Traefik's own Docker network (separate
  host/daemon), so they're routed via static `loadBalancer` URLs in the file
  provider instead of Docker-label auto-discovery — that's the actual reason for the
  docker-vs-not split, not "some things aren't containerized." (LazyDocker being one
  of media's own services is itself evidence media runs Docker too.)
- **`rpi`** (`10.10.0.30`, SSH alias `rpi`) — a dedicated Raspberry Pi running
  Hyperion (ambient lighting). Not part of the Traefik/Docker split above, just a
  third always-on LAN device with its own example.com name.

## Traefik

Runs as a Docker container on `work` (`~/www/traefik/docker-compose.yml`), ports
80/443/8080 (8080 = insecure API/dashboard). Two ways a service gets routed:

1. **Docker label auto-discovery** (`--providers.docker=true`) — for containers on
   the *same* Docker daemon Traefik's socket is mounted from (i.e., anything running
   on `work`). Service name in the router is `<name>@docker`.
2. **File provider** (`--providers.file.directory=/dynamic`, watching
   `~/www/traefik/dynamic/*.yml`) — for everything else: media's services (different
   host entirely) and the one legacy TLS-cert case (`csm-tls.yml`, see its own
   comments for why — Web Push/Service Workers need a real secure context, so
   `app.dev.local.test` gets a self-signed file-provider cert alongside the example.com
   wildcard).

**Certificates**: a single wildcard cert for `example.com` + `*.example.com`, issued via
Let's Encrypt's DNS-01 challenge against Cloudflare's API (`CF_DNS_API_TOKEN` in
`~/www/traefik/.env`) — DNS-01 because these names aren't publicly reachable on `:80`
for an HTTP-01 challenge. Requested as the `websecure` entrypoint's *default* cert, so
every current and future `*.example.com` router gets it automatically — adding a new
router never means touching cert config.

**Adding a new example.com service** (matches what the cards-migration task actually
did): if it's a container on `work`, just add Traefik labels to its compose file — no
edit needed here. If it's on `media` (or anywhere else off-host), add a `routers:` +
`services:` pair to `ac495-sites.yml` following the existing "Media server sites"
block's style (`entryPoints: [websecure]` only, static `loadBalancer` url).

## Pi-hole and split-horizon DNS — the actual gotcha

Pi-hole runs on `media` and provides LAN-local DNS overrides for `*.example.com`,
pointing each name at whichever machine actually hosts it (`work` for
Traefik/Docker-routed names, `media` itself for media's own services). A LAN client
using Pi-hole for DNS hits the target machine **directly** — fast, works even if the
internet/tunnel is down, gets the real wildcard cert served locally by Traefik.

**The gotcha**: anything that *doesn't* use Pi-hole for DNS — a Docker container with
its own hardcoded `resolv.conf`, a device on a guest network, anything remote — gets
the **public** DNS answer instead, which is Cloudflare's proxied edge IP, not the LAN
IP. That forces the request through the internet and back in via the Tunnel/Access
path below, even though the client was on the same LAN the whole time. This is
exactly what broke the assumption during the cards-domain migration: `homie-app`'s
own container resolv.conf pointed at `10.10.0.20`/`10.10.0.1` directly rather than
through Pi-hole, so `getent hosts sonarr.example.com` from inside it returned
Cloudflare's edge IPs, and a `curl` to `sonarr.example.com` from there got a 302
(Cloudflare Access) instead of hitting Sonarr.

**Practical rule**: never point anything that does *server-side* polling/fetching of
a LAN service (an API client, a health check, a cron job) at its `*.example.com` name
unless you've confirmed that specific process's DNS actually goes through Pi-hole.
When in doubt, use the raw LAN IP:port for machine-to-machine traffic and reserve
`*.example.com` names for the human-facing click-through links — that was the exact
distinction the cards migration plan had to draw between `cards.url` (safe to
convert) and `card_apis.base_url` (must stay a raw IP).

## Cloudflare Tunnel / Access

A named tunnel (`home`, config at `~/www/traefik/cloudflared-media-config.yml`,
credentials file referenced by UUID) runs on `media`, giving external/remote access
to `*.example.com` without opening any port on the home router. Traffic that resolves
to Cloudflare's public edge (see the DNS gotcha above, or genuinely external clients)
gets gated by Cloudflare Access before reaching the tunnel — confirmed by an observed
302 on a direct `curl` from outside the LAN-DNS path, and per-service ingress rules
now cover every `media`-hosted hostname individually (not just a single-hostname
catch-all), so every current `*.example.com` name is confirmed gated the same way.

## Known limitations

- This doc reflects the Traefik/Pi-hole/Tunnel config as read directly from files —
  it does not cover Cloudflare Access policy configuration itself (which lives in the
  Cloudflare dashboard, not any local file) or Pi-hole's own override list contents
  (not inspected directly — inferred from Traefik's routing and the DNS-gotcha test
  in the cards-migration session).
