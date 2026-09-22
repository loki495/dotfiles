#!/usr/bin/env bash
name="world"
echo "hello, $name!"
if [ -n "$name" ]; then
  echo "done"
fi
value="$(printf '%s' "$name")"
cat <<HTML
<strong>Hello</strong>
HTML
