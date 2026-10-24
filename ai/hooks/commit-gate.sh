#!/usr/bin/env bash
# PreToolUse(Bash): checks at `git commit`.
#  - deny a message that says "Docs: updated" when the commit touches no doc or test file
#  - otherwise add context: code-only commit with no docs/tests, and atlas subsystems the commit touches
# A message claims docs were updated when it says so in a `Docs: updated` line or in prose (docs/documentation/README
# near updated/updates). Silent when nothing applies. Dibs trouble only drops the atlas note. HELPER overrides the helper (tests).
input=$(cat)
cmd=$(jq -r '.tool_input.command // ""' <<<"$input")
grep -Eq '(^|[^[:alnum:]_-])git([[:space:]]+-[^[:space:]]+([[:space:]]+[^-[:space:]][^[:space:]]*)?)*[[:space:]]+commit([[:space:]]|$)' <<<"$cmd" || exit 0
cwd=$(jq -r '.cwd // empty' <<<"$input"); cd "${cwd:-.}" 2>/dev/null || exit 0
git rev-parse --show-toplevel >/dev/null 2>&1 || exit 0
top=$(git rev-parse --show-toplevel)

files=$(git diff --cached --name-only)
grep -Eq '(^|[[:space:]])(-[[:alnum:]]*a[[:alnum:]]*|--all)([[:space:]]|$)' <<<"$cmd" && files=$(printf '%s\n%s\n' "$files" "$(git diff --name-only)")
files=$(sed '/^$/d' <<<"$files" | sort -u)
[ -n "$files" ] || exit 0

docs='(\.md$|\.rst$|^docs?/|(^|/)tests?/|(^|/)test_|_test\.|\.test\.|\.spec\.|(^|/)SKILL\.md$)'
has_docs=0; grep -Eq "$docs" <<<"$files" && has_docs=1

emit() { jq -n --arg d "$1" --arg r "$2" --arg c "$3" \
  'if $d=="deny" then {hookSpecificOutput:{hookEventName:"PreToolUse",permissionDecision:"deny",permissionDecisionReason:$r}}
   else {hookSpecificOutput:{hookEventName:"PreToolUse",additionalContext:$c}} end'; exit 0; }

claim='docs:[[:space:]]*updated|(docs?|documentation|readme)[^.[:space:]]*[[:space:]]+(\w+[[:space:]]+){0,2}updated|updated?[[:space:]]+(the[[:space:]]+)?(docs?|documentation|readme)'
if [ "$has_docs" = 0 ] && ! grep -Eqi 'docs:[[:space:]]*n/a' <<<"$cmd" && grep -Eqi "$claim" <<<"$cmd"; then
  emit deny "The commit message says docs were updated, but no doc or test file is staged. Stage the docs/tests, or drop that line."
fi

notes=()
if [ "$has_docs" = 0 ] && ! grep -Eqi 'docs:[[:space:]]*(updated|n/a)' <<<"$cmd"; then
  notes+=("No doc or test file is in this commit. If the change makes a doc wrong or needs a test, include it in the same commit; otherwise add a line 'Docs: n/a (reason)'.")
fi
helper=${HELPER:-$(dirname "$(readlink -f "$0")")/atlas-helper.py}
touched=$(timeout 20 "$helper" touched "$top" $files 2>/dev/null | jq -r '(.subsystems // []) | join(", ")' 2>/dev/null)
[ -n "$touched" ] && notes+=("This commit touches feature-atlas subsystems: $touched. Update those atlas comments and stamp them with this commit's SHA (the push gate checks it). Do not mention the atlas in the commit message.")
[ ${#notes[@]} -gt 0 ] && emit ctx "" "$(printf '%s ' "${notes[@]}")"
exit 0
