#!/usr/bin/env python3
"""Copy a verified archived runtime into a new directory for replay.

Historical entry points are named INSTRUCTIONS.md so skill discovery does not
mistake archived versions for additional active skills. This command restores
the canonical SKILL.md name without changing its bytes.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

from check import Archive, ROOT, frozen_versions, read_json


def materialize(variant: str, output: Path) -> list[str]:
    evidence = read_json(ROOT / "evidence.json")
    archive = Archive(ROOT, evidence["recorded_files_sha256"])
    versions = frozen_versions(archive, evidence)
    if variant not in versions:
        raise ValueError(f"Unknown archived variant: {variant}")
    destination = output.expanduser().absolute()
    if destination.exists() or destination.is_symlink():
        raise ValueError("Output must be a new directory; existing paths are never overwritten")
    if any(parent.is_symlink() for parent in destination.parents):
        raise ValueError("Output parent paths must not be symlinks")
    destination.mkdir(parents=True, exist_ok=False)
    written = []
    for name, raw in versions[variant].items():
        path = destination / name
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("xb") as handle:
            handle.write(raw)
        written.append(name)
    return written


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--variant", required=True, help="Archived variant, such as v4 or v5")
    parser.add_argument("--out", type=Path, required=True, help="New output directory")
    args = parser.parse_args(argv)
    try:
        written = materialize(args.variant, args.out)
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"Could not materialize runtime: {error}", file=sys.stderr)
        return 1
    print(f"Copied {len(written)} verified runtime files for {args.variant} to {args.out}")
    print("No model responses were generated or graded.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
