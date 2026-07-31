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
- If the project has a dev browser available (Playwright, etc.), verify at a real
  small viewport (e.g. ~390px wide), not just by shrinking a desktop browser window.
- If the project supports both light and dark mode, verify both — don't assume
  whichever theme happens to be active during development is the only one that
  matters.
