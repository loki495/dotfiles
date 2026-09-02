---
topic: neovim-treesitter-parser-lookup
tags: [nvim, neovim, treesitter, lua, testing]
---

Two related gotchas discovered while building a test that simulates a missing
treesitter parser (Neovim 0.12.5):

1. **Parser file lookup is a glob, not an exact match.** Neovim resolves a
   language's parser via something like `parser/<lang>.*` under runtimepath, not
   a literal `parser/<lang>.so` check. Renaming `rust.so` to `rust.so.bak` in the
   same directory does NOT hide it from lookup - the glob still matches the
   `.bak`-suffixed file and it loads normally. To genuinely simulate "parser not
   installed," move the file fully out of the parser directory (e.g. to `/tmp`),
   don't just rename it in place.

2. **`vim.treesitter.get_parser()` and `vim.treesitter.start()` fail by
   returning `nil`/`false`, not by throwing.** A bare `pcall(vim.treesitter.start,
   buf, lang)` reports `ok = true` even when the language/parser genuinely
   doesn't exist, because no Lua error was raised - `pcall` only catches thrown
   errors, not "successfully returned a failure value." To actually detect
   failure, check the return value itself (`get_parser(...) == nil`) or check
   `vim.treesitter.highlighter.active[bufnr] ~= nil` after calling `start()`.

Both confirmed via direct headless testing on Neovim v0.12.5 (2026-09-02).
