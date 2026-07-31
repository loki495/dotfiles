# OpenCart Legacy (1.5.6)

Applies only to OpenCart projects. Never mix with Laravel conventions — this is a
different architecture entirely.

## Structure

- Classic OpenCart MVC: `controller/`, `model/`, `view/` under both `catalog/` and
  `admin/`. Registry-based DI, no Composer autoloading for the core.
- Prefer putting logic in **models**, consistent with OpenCart's own conventions —
  controllers stay thin here too, even though the mechanism is different from Laravel.
- Composer may exist in some sub-path or at project root for specific add-ons, but it's
  not the norm. Don't assume Composer autoloading is wired into the core app.

## vQmod

- vQmod is likely installed. Modifications are defined as XML under `vqmod/xml/`.
- The actual files that **run** are the compiled/merged versions under
  `vqmod/vqcache/` — when debugging runtime behavior, check vqcache, not just the
  original source file, since the original may differ from what's actually executing.
- vQmod is effectively deprecated as a pattern but still relied upon in this codebase.
  Don't propose ripping it out wholesale. New changes can be made as direct edits to
  core files (see below) rather than new vqmod XML, but existing vqmods stay as-is
  unless there's a specific reason to migrate one.

## Editing core files

- Historically the preference was to extend rather than modify core files directly.
  That preference still applies as a default — extend where reasonable.
- However, since the project is under git, directly rewriting core files is acceptable
  when extending isn't practical. Git history is the safety net, not strict
  non-modification.

## PHP version

- Match whatever PHP version the **production machine** actually runs — this varies by
  project and could be anywhere from 7.3 up to 8.x. Don't assume 7.3 as a hard floor;
  check the actual production version for the specific project (ask if unknown) and
  set the dev container to match exactly.
- Because the PHP version varies per project and may be old, don't assume modern PHP
  features (typed properties, enums, match expressions, etc.) are available unless
  confirmed for that project's actual PHP version.

## Avoid hardcoding

General rule (settings/config/env/language files over literals) is in
`~/.claude/CLAUDE.md`'s "Avoid hardcoding" section — this note is the OpenCart-
specific mechanism. Content, thresholds, labels, and anything customizable should
come from the database or a module's settings (typically `theme_settings`) — not
hardcoded in templates/controllers. This matters more here than in a typical
single-site project because these OpenCart sites are often multi-site/multi-theme
off shared core code — a hardcoded value that's fine for one site silently breaks or
misrepresents another. When adding something that could plausibly need to differ per
site or change without a code deploy, default to a settings field over a literal.

## Tooling

- No tooling (Pint, PHPStan, Rector, Pest) is enforced automatically on OpenCart
  projects. If a specific project wants any of these active, that's noted in that
  project's own `.claude/project.md` — check there before assuming none apply.
