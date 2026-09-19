# Infrastructure Setup

This public repository contains only the dotfiles installer and configuration templates.
Real infrastructure configuration (Traefik routes, home-lab topology, credentials) lives in
a **private `dotfiles-private` repository** to keep your network topology and services private.

## Setup After Cloning

After cloning this repo:

```bash
# 1. Clone the private infrastructure repo (you'll need access)
git clone git@github.com:andres/.../dotfiles-private.git ~/.dotfiles-private

# 2. Symlink the private traefik config
ln -s ~/.dotfiles-private/traefik traefik

# 3. Symlink the private AI skills
ln -s ~/.dotfiles-private/ai/skills/ac495-infrastructure ai/skills/ac495-infrastructure
```

The `.gitignore` is pre-configured to exclude these symlink targets, so the private repo
stays private and the public repo stays clean.

## What's Private

The `dotfiles-private` repo contains:
- `traefik/` — Traefik reverse-proxy configuration (routes, service discovery, TLS)
- `ai/skills/ac495-infrastructure/` — Home-lab topology, service inventory, infrastructure as code

## What's Public

This repo (public) contains:
- Install scripts and dotfiles templates
- Generic AI skills and tools
- CI configuration and testing setup
- No hostnames, IPs, credentials, or infrastructure details
