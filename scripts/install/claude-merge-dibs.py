#!/usr/bin/env python3
"""Render Claude's config with only the managed Dibs entry changed."""
import json
from pathlib import Path
import sys

target, template, root = map(Path, sys.argv[1:])
config = json.loads(target.read_text()) if target.exists() else {}
if not isinstance(config, dict):
    raise ValueError('Claude config must be a JSON object')
servers = config.setdefault('mcpServers', {})
if not isinstance(servers, dict):
    raise ValueError('Claude mcpServers must be a JSON object')
entry = json.loads(template.read_text())
entry['command'] = entry['command'].replace('${DOTFILES_ROOT}', str(root))
servers['dibs'] = entry
json.dump(config, sys.stdout, indent=2, ensure_ascii=False)
print()
