#!/usr/bin/env python3
"""Resolve a Claude hook or MCP launcher's original caller to its agent process."""
import argparse
import os
from pathlib import Path


def agent_pid(caller_pid):
    pid = caller_pid
    seen = set()
    for _ in range(64):
        if pid <= 1 or pid in seen:
            break
        seen.add(pid)
        try:
            proc = Path('/proc') / str(pid)
            stat = (proc / 'stat').read_text().rsplit(')', 1)[1].split()
            if stat[0] == 'Z':
                break
            comm = (proc / 'comm').read_text().strip()
            args = (proc / 'cmdline').read_bytes().split(b'\0')
            # Service names are subcommands, not arbitrary prompt or option values.
            if comm == 'claude' and (len(args) < 2 or args[1] not in (b'daemon', b'supervisor')):
                return pid
            pid = int(stat[1])
        except (OSError, ValueError, IndexError):
            break
    return caller_pid


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--caller-pid', type=int, required=True)
    args = parser.parse_args()
    if args.caller_pid <= 0:
        parser.error('--caller-pid must be positive')
    caller = os.getppid() if args.caller_pid == os.getpid() else args.caller_pid
    print(agent_pid(caller))


if __name__ == '__main__':
    main()
