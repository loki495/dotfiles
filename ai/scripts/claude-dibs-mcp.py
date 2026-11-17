#!/usr/bin/env python3
"""Launch Dibs MCP with the same host agent identity as Claude hooks."""
import importlib.util
import os
from pathlib import Path

caller = os.getppid()
spec = importlib.util.spec_from_file_location('agent_pid', Path(__file__).resolve().with_name('agent-pid.py'))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
pid = str(module.agent_pid(caller))
compose = str(Path.home() / 'www/personal/dibs/docker-compose.yml')
os.execvp('docker', ['docker', 'compose', '-f', compose, 'exec', '-T', '-u', 'www-data',
                     '-e', 'DIBS_AGENT_PID=' + pid, '-e', 'DIBS_CLIENT_PID=' + pid,
                     'app', 'php', 'artisan', 'mcp:start', 'todo'])
