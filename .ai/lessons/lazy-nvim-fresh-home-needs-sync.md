---
topic: lazy-nvim-fresh-home-needs-sync
tags: [nvim, neovim, lazy.nvim, testing, ci, general]
---

A genuinely fresh `$HOME` (any container, a CI job, a new machine) that has
never launched Neovim before will have lazy.nvim's plugin *specs* discoverable
(they're just files in the config repo) but none of the actual plugins cloned
or built. On a real dev machine this is invisible — lazy.nvim already did this
once, ages ago, from ordinary usage — so it's easy to forget as a setup step
entirely.

The failure mode isn't "plugin missing" in an obvious way. Plugins with a
native compile step (e.g. `telescope-fzf-native.nvim`'s `.so`) throw a hard Lua
error partway through lazy.nvim's plugin-loading sequence when their binary
doesn't exist yet. Depending on load order, that error can interrupt Neovim's
own startup *before* later `FileType`/other autocmds ever get registered —
so unrelated-looking features (in one confirmed case: treesitter highlighting
autocmds for several filetypes, unrelated to the broken plugin) silently never
activate, with no direct error pointing at the actual cause.

Fix: explicitly bootstrap once, before relying on anything plugin-dependent in
an automated/fresh-environment context:

    nvim --headless "+Lazy! sync" +qa

`Lazy! sync` (not just `Lazy! install`) both installs missing plugins and runs
their build steps. Wrap in a `timeout` in CI (compiling native extensions can
be slow, and the failure mode without a timeout is a silent hang, not a
fast error). Confirmed 2026-09-02: skipping this step caused 6 of 11 languages
in an otherwise-correct treesitter-highlighting test to fail; adding just this
one step (no other changes) took it to 0 failures.
