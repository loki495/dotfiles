---
name: frontend-stack
description: Frontend conventions across Laravel and OpenCart: Tailwind, JS (Alpine vs jQuery), CSS, and responsive/mobile verification. Use for any UI or frontend work.
---

# Frontend Stack

Applies across both Laravel and OpenCart projects, with some split by project type.

## Tailwind

- Use whichever Tailwind version the project already has configured. Check
  `package.json` / `tailwind.config.js` (v3) or the CSS-based config (v4) before
  assuming.
- For new projects/new Tailwind setups, prefer the latest stable version.
- No required utility-class ordering convention — just write classes in a sensible,
  readable grouping (e.g. layout → spacing → typography → color → state), nothing
  more rigid than that.

## JavaScript

- **Laravel/Livewire projects:** prefer Alpine.js for client-side interactivity (see
  `livewire-components.md` for when Alpine vs Livewire makes sense). Avoid introducing
  jQuery into Laravel projects.
- **OpenCart (legacy) projects:** jQuery is fine — OpenCart ships with it and fighting
  that is not worth it. No need to modernize existing jQuery usage unless there's a
  specific reason to.

## CSS

- No particular pattern beyond "something sensible" — match whatever convention
  already exists in a given project (utility-first via Tailwind, scoped component
  styles, etc.) rather than introducing a new approach mid-project.

## Mobile & responsive

- Check small-viewport layout proactively on any UI work (new components, modals/
  popups, forms, cards) — don't wait to be told. This has been the single most
  common thing missed across projects: squished inputs, off-screen fields,
  horizontal-scroll overflow, buttons too small for touch.
- Verify UI-touching changes in a real browser before calling them done: a Playwright
  (or other dev browser) screenshot at a real phone viewport (~390px wide) first, then
  desktop — not just by shrinking a desktop browser window, and not just by reading
  the code. Look at the screenshot yourself rather than asking Andres to check.
- Andres often uses web apps from iOS, including as home-screen PWAs (no browser
  chrome). Behavior there differs from Safari and from Playwright, so keep in mind:
  - Aggressive caching of JS/CSS — use cache-busting (versioned asset URLs) so a
    change doesn't require re-adding the home-screen icon.
  - Safe-area insets and the on-screen keyboard: fixed footers/composers must stay
    pinned to the bottom with no blank area below, and focusing a textarea must not
    scroll the page past the viewport.
  - Enter in a textarea on mobile inserts a newline; it must never submit.
  - Web push/notifications only work from the home-screen app and need an explicit
    user-gesture permission prompt.
  When a bug only reproduces in the PWA, say so rather than concluding from a
  Playwright run that it works.
- If the project supports both light and dark mode, verify both — don't assume
  whichever theme happens to be active during development is the only one that
  matters.
