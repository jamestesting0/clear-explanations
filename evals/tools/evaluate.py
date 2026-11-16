#!/usr/bin/env python3
"""Create independent prompts, invoke an optional adapter, collect, check, report."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import signal
import subprocess
import sys

from core import (BUNDLE_MODE, BUNDLE_NOTE, SCHEMA, bundle_digest, canonical, collect, evaluate_many, format_packet,
                  now, packet_integrity, paths, read_index, read_json, read_runtime_bundle,
                  select_packets, sha, valid_id, validate_cases, within, write_json)
from report import render_report
from review_packets import import_blind_reviews, make_review_packets


def make_packets(args):
    cases = validate_cases(read_json(args.cases))
    wanted = set(args.ids.split(",")) if args.ids else None
    cases = [c for c in cases if (args.split == "all" or c["split"] == args.split)
             and (not wanted or c["id"] in wanted)]
    if not cases or (wanted and wanted - {c["id"] for c in cases}):
        raise ValueError("Selection is empty or includes unknown/excluded case IDs")
    variants, seen = {}, set()
    for option in ("skill", "bundle"):
        for value in getattr(args, option, None) or []:
            name, separator, source = value.partition("=")
            valid_id(name)
            if not separator or not source or name.casefold() in seen:
                raise ValueError("Use unique variants across --skill VARIANT=PATH and --bundle VARIANT=DIR")
            seen.add(name.casefold())
            if option == "bundle":
                variants[name] = (None, read_runtime_bundle(source))
            else:
                raw = None if source == "none" else Path(source).read_bytes()
                if raw is not None:
                    raw.decode("utf-8")
                variants[name] = (raw, None)
    if not variants:
        raise ValueError("Provide at least one --skill VARIANT=PATH or --bundle VARIANT=DIR")
    run = Path(args.out)
    if run.exists() and any(run.iterdir()):
        raise ValueError("Run directory must be new or empty; frozen runs are never overwritten")
    run.mkdir(parents=True, exist_ok=True)
    write_json(run / "cases.json", cases)
    index = {"schema_version": SCHEMA, "name": args.name or run.name, "created_at": now(),
             "source_cases_sha256": sha(Path(args.cases).read_bytes()), "packets": []}
    if any(resources is not None for _, resources in variants.values()):
        index["bundle_note"] = BUNDLE_NOTE
    for variant, (raw, resources) in variants.items():
        bundle_fields = {}
        if resources is not None:
            frozen = []
            for resource_path, contents in resources:
                frozen_path = f"skills/{variant}/{resource_path}"
                destination = run / frozen_path
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(contents)
                frozen.append({"resource_path": resource_path, "frozen_path": frozen_path,
                               "sha256": sha(contents), "bytes": len(contents)})
            root = next(resource for resource in frozen if resource["resource_path"] == "SKILL.md")
            skill_path, skill_hash = root["frozen_path"], root["sha256"]
            bundle_fields = {"guidance_mode": BUNDLE_MODE, "runtime_resources": frozen,
                             "bundle_sha256": bundle_digest(frozen)}
        else:
            skill_path = f"skills/{variant}.md" if raw is not None else None
            skill_hash = sha(raw) if raw is not None else None
        if raw is not None:
            destination = run / skill_path
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(raw)
        for case in cases:
            prompt = format_packet(case, skill=raw, resources=resources)
            relative = f"packets/{variant}/{case['id']}.txt"
            destination = run / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(prompt)
            index["packets"].append({"case_id": case["id"], "variant": variant, "split": case["split"],
                                     "prompt_path": relative, "prompt_sha256": sha(prompt),
                                     "frozen_skill_path": skill_path, "skill_sha256": skill_hash,
                                     "case_sha256": sha(canonical(case)), **bundle_fields})
    write_json(run / "index.json", index)
    print(f"Created {len(index['packets'])} packets in {run}")


def import_response(args):
    valid_id(args.case)
    index, cases = read_index(args.run)
    packet = select_packets(index, args.variant, args.case)[0]
    metadata = read_json(args.metadata) if args.metadata else {}
    if args.transport:
        metadata["transport"] = args.transport
    if args.model:
        metadata["model_requested"] = args.model
    result = collect(args.run, packet, cases[packet["case_id"]], Path(args.response).read_bytes(), metadata)
    print(f"Collected {result['variant']}/{result['case_id']} sha256={result['response_sha256']}")


def run_adapter(args):
    command = json.loads(args.command_json)
    if not isinstance(command, list) or not command or any(not isinstance(a, str) or not a for a in command):
        raise ValueError("--command-json must be a nonempty JSON array of nonempty strings")
    if args.timeout <= 0:
        raise ValueError("Timeout must be positive")
    index, cases = read_index(args.run)
    packets = select_packets(index, args.variant, args.ids)
    failed = 0
    for packet in packets:
        output, meta_path = paths(args.run, packet)
        if output.exists() or meta_path.exists():
            if args.skip_existing:
                print(f"Skipped existing {packet['variant']}/{packet['case_id']}")
                continue
            raise ValueError(f"Response already exists: {output}; use a new run or --skip-existing")
        integrity = packet_integrity(args.run, packet, cases[packet["case_id"]])
        if integrity:
            raise ValueError("Altered packet: " + "; ".join(integrity))
        metadata = {"transport": "external-command", "adapter_command": command,
                    "prompt_sha256_role": "exact_adapter_stdin",
                    "model_requested": args.model, "model_observed": None,
                    "started_at": now(), "timeout_seconds": args.timeout}
        stdout, stderr, exit_code = b"", b"", None
        try:
            process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE, cwd=args.cwd, start_new_session=os.name == "posix")
            try:
                stdout, stderr = process.communicate(within(args.run, packet["prompt_path"]).read_bytes(),
                                                     timeout=args.timeout)
                status = "completed" if process.returncode == 0 else "command_error"
            except subprocess.TimeoutExpired:
                if os.name == "posix":
                    os.killpg(process.pid, signal.SIGKILL)
                else:
                    process.kill()
                stdout, stderr = process.communicate()
                status = "timeout"
            exit_code = process.returncode
        except OSError as error:
            status, stderr = "launch_error", str(error).encode("utf-8")
        metadata.update(completed_at=now(), status=status, exit_code=exit_code)
        collect(args.run, packet, cases[packet["case_id"]], stdout, metadata, stderr)
        print(f"{packet['variant']}/{packet['case_id']}: {status}, {len(stdout)} bytes", flush=True)
        failed += status != "completed"
    return int(failed > 0)


def check_or_report(args):
    result = evaluate_many(args.run, args.reviews)
    destination = Path(args.out) if args.out else Path(args.run[0]) / ("report.html" if args.action == "report" else "checks.json")
    if args.action == "report":
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(render_report(result), encoding="utf-8")
    else:
        write_json(destination, result)
    records = result["results"]
    print(f"{sum(r['deterministic_pass'] for r in records)}/{len(records)} pass deterministic checks; "
          f"{sum(r['review_state'] == 'valid' for r in records)}/{len(records)} have valid semantic reviews")
    print(f"Wrote {destination}")
    return int(args.action == "check" and any(not r["deterministic_pass"] for r in records))


def review_template(args):
    result = evaluate_many(args.run)
    template = {"schema_version": SCHEMA, "reviewer": "REPLACE_WITH_REVIEWER_AND_METHOD", "reviews": []}
    for record in result["results"]:
        if record["errors"]:
            continue
        template["reviews"].append({"variant": record["variant"], "case_id": record["case_id"],
                                    "response_sha256": record["response_sha256"],
                                    "verdict": "UNREVIEWED", "rationale": "", "criteria": []})
    destination = Path(args.out)
    if destination.exists():
        raise ValueError("Review template destination already exists")
    write_json(destination, template)
    print(f"Wrote {destination}; UNREVIEWED is intentionally invalid until a reviewer completes it")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_subparsers(dest="action", required=True)
    packets = actions.add_parser("packets", help="Freeze cases/skills and create independent task prompts",
                                 epilog=BUNDLE_NOTE)
    packets.add_argument("--cases", required=True)
    packets.add_argument("--out", required=True)
    packets.add_argument("--skill", action="append", metavar="VARIANT=PATH",
                         help="Freeze one UTF-8 skill file; PATH 'none' means baseline (repeatable)")
    packets.add_argument("--bundle", action="append", metavar="VARIANT=DIR",
                         help="Freeze SKILL.md plus direct references/*.md and inject their exact contents; "
                              "no symlinks or recursive traversal (repeatable)")
    packets.add_argument("--split", choices=("all", "development", "validation", "holdout"), default="all")
    packets.add_argument("--ids", help="Comma-separated case IDs")
    packets.add_argument("--name")
    packets.set_defaults(function=make_packets)
    collect_parser = actions.add_parser("collect", help="Import exact response bytes and provenance")
    collect_parser.add_argument("--run", required=True)
    collect_parser.add_argument("--variant", required=True)
    collect_parser.add_argument("--case", required=True)
    collect_parser.add_argument("--response", required=True)
    collect_parser.add_argument("--metadata", help="JSON object containing observed provenance")
    collect_parser.add_argument("--transport")
    collect_parser.add_argument("--model", help="Requested model; never treated as observed model")
    collect_parser.set_defaults(function=import_response)
    runner = actions.add_parser("run", help="Invoke a fresh external command for each packet")
    runner.add_argument("--run", required=True)
    runner.add_argument("--command-json", required=True, help='Argument array, e.g. ["python", "adapter.py"]')
    runner.add_argument("--variant")
    runner.add_argument("--ids")
    runner.add_argument("--timeout", type=float, default=180)
    runner.add_argument("--cwd", help="Adapter working directory")
    runner.add_argument("--model", help="Requested model identifier, if known")
    runner.add_argument("--skip-existing", action="store_true")
    runner.set_defaults(function=run_adapter)
    for action in ("check", "report"):
        command = actions.add_parser(action, help="Recompute checks" if action == "check" else "Render safe HTML with paired comparisons")
        command.add_argument("--run", required=True, action="append", help="Repeat to compare separately scheduled runs")
        command.add_argument("--reviews", help="Separate completed semantic review JSON")
        command.add_argument("--out")
        command.set_defaults(function=check_or_report)
    template = actions.add_parser("review-template", help="Create an explicitly unreviewed review skeleton")
    template.add_argument("--run", required=True, action="append")
    template.add_argument("--out", required=True)
    template.set_defaults(function=review_template)
    blind = actions.add_parser("review-packets", help="Prepare separate blind reviewer inputs and a private identity key",
                               epilog="Share only the reviewer directory. This prepares inputs; it does not perform "
                                      "independent review or hide identity clues within response text. Mechanical "
                                      "constraint failures remain reviewable; missing/stale/failed responses are rejected.")
    blind.add_argument("--run", required=True, action="append")
    blind.add_argument("--out", required=True, help="New or empty reviewer directory")
    blind.add_argument("--key", required=True, help="New private mapping file outside the reviewer directory")
    blind.add_argument("--rubric", help="Optional separate JSON rubric, copied only into reviewer inputs")
    blind.set_defaults(function=make_review_packets)
    unblind = actions.add_parser("review-import", help="Validate and resolve blind reviews into the existing review schema")
    unblind.add_argument("--run", required=True, action="append")
    unblind.add_argument("--packets", required=True, help="Original blind reviewer directory")
    unblind.add_argument("--key", required=True, help="Separate private identity mapping")
    unblind.add_argument("--reviews", required=True, help="Completed blind review JSON with review_id entries")
    unblind.add_argument("--out", required=True, help="New completed review JSON for check/report")
    unblind.set_defaults(function=import_blind_reviews)
    args = parser.parse_args(argv)
    try:
        return args.function(args) or 0
    except (ValueError, OSError, KeyError, TypeError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
