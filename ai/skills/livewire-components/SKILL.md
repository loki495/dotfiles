---
name: livewire-components
description: Livewire component conventions: version detection (4 vs 3/Volt), single-file class components, Flux UI, Alpine.js for client interactivity, and optimistic updates. Use for Livewire work.
---

# Livewire Components

Applies to Laravel/Livewire projects (not OpenCart).

## Version detection first

Check `composer.json` for the Livewire version before writing any component code:

- **Livewire 4** → use single-file class components (the modern syntax that absorbed
  Volt's patterns — logic and view together in one file, class-based).
- **Livewire 3 with Volt** → several active projects still use Volt's single-file
  syntax on v3. Match the existing syntax in that project rather than assuming v4
  conventions apply.

If a project's version is ambiguous, or it's a new component in a project you haven't
touched yet, **ask** rather than assume which style to use.

## Default for new projects

For brand new projects/components, default to **Livewire 4 single-file class
components**. This is the preferred modern approach going forward.

## Flux UI

Prefer Flux components over hand-rolled Tailwind markup **when a suitable free Flux
component exists** for the job (buttons, form inputs, modals, etc.). Don't force Flux
where it doesn't fit, and don't reach for paid/pro components by default — check what's
actually available in the project's Flux tier first.

## Alpine.js for client-only interactivity

It's fine — encouraged — to reach for Alpine.js for interactivity that doesn't need a
server roundtrip: toggling visibility, simple UI state, dropdowns, tabs, local form
feedback, etc. Not everything needs to go through a Livewire request. Use Livewire for
things that need server state/data; use Alpine for things that are purely client-side.

## Optimistic updates

Where it makes sense (e.g. toggles, likes, simple state flips, list reordering),
prefer optimistic UI updates — update the UI immediately and reconcile with the
server response — rather than waiting on a round trip before reflecting the change.
Don't force this for actions where the server response actually matters to what's
displayed (e.g. validation-dependent results).
