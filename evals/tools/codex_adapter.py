#!/usr/bin/env python3
"""Run one fresh Codex request; stdout contains only its final response."""
from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cwd", help="Workspace for the explanation request")
    parser.add_argument("--model", help="Optional operator-selected model")
    args = parser.parse_args()
    prompt = sys.stdin.buffer.read()
    with tempfile.TemporaryDirectory(prefix="explain-response-") as temporary:
        output = Path(temporary) / "response.md"
        workspace = Path(args.cwd).resolve() if args.cwd else Path(temporary) / "workspace"
        if not args.cwd:
            workspace.mkdir()
        command = ["codex", "exec", "--ephemeral", "--skip-git-repo-check",
                   "--sandbox", "read-only", "--color", "never",
                   "--output-last-message", str(output), "--cd", str(workspace)]
        if args.model:
            command.extend(["--model", args.model])
        command.append("-")
        try:
            completed = subprocess.run(command, input=prompt, capture_output=True)
        except FileNotFoundError:
            print("Codex CLI was not found on PATH.", file=sys.stderr)
            return 127
        sys.stderr.buffer.write(completed.stderr)
        if completed.returncode:
            sys.stderr.buffer.write(completed.stdout)
            return completed.returncode
        if not output.is_file() or not output.stat().st_size:
            print("Codex returned no final response file; diagnostics are not an answer.", file=sys.stderr)
            return 1
        sys.stdout.buffer.write(output.read_bytes())
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
