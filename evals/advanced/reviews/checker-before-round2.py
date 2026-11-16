#!/usr/bin/env python3
"""Verify the archived advanced benchmark, without generating or grading answers."""
from __future__ import annotations

import argparse
from collections import Counter
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent / "tools"))
from core import bundle_digest, canonical, constraint_checks, read_runtime_bundle, sha, validate_cases, word_count

DIMENSIONS = {"accuracy", "evidence", "coverage", "clarity", "structure", "fit"}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def stats(records):
    require(bool(records), "Cannot summarize an empty group")
    verdicts = Counter(r["review"]["verdict"] for r in records)
    return {
        "responses": len(records),
        "pass": sum(r["fully_reviewed_pass"] for r in records),
        "partial": verdicts["partial"],
        "fail": verdicts["fail"],
        "critical_failures": sum(bool(r["review"].get("critical_errors")) or any(r["review"]["dimensions"][k] == 0 for k in ("accuracy", "evidence", "coverage", "fit")) for r in records),
        "mean_words": sum(r["word_count"] for r in records) / len(records),
        "mean_characters": sum(len(r["response"]) for r in records) / len(records),
        "mean_score": sum(r["review"]["score"] for r in records) / len(records),
    }


def verify(require_current=False):
    evidence = read_json(ROOT / "evidence.json")
    require(evidence.get("schema_version") == 1, "Unsupported evidence schema")
    for name, digest in evidence["recorded_files_sha256"].items():
        path = (ROOT / name).resolve()
        require(ROOT in path.parents, f"Recorded path escapes archive: {name}")
        require(sha(path.read_bytes()) == digest, f"Recorded file changed: {name}")
    for name, version in evidence["variants"].items():
        resources = dict(read_runtime_bundle(ROOT / version["directory"]))
        require(sha(resources["SKILL.md"]) == version["skill_sha256"], f"Frozen skill hash mismatch: {name}")
        if version.get("bundle_sha256"):
            manifest = [{"resource_path": path, "sha256": sha(raw), "bytes": len(raw)} for path, raw in resources.items()]
            require(bundle_digest(manifest) == version["bundle_sha256"], f"Frozen bundle hash mismatch: {name}")
        else:
            require(set(resources) == {"SKILL.md"}, f"Single-file variant unexpectedly contains references: {name}")
    main_cases = validate_cases(read_json(ROOT / "cases.json"))
    short_cases = validate_cases(read_json(ROOT / "short-cases.json"))
    cases = {c["id"]: c for c in main_cases + short_cases}
    require(len(cases) == len(main_cases) + len(short_cases), "Duplicate hard/short case ID")
    require(len(main_cases) == 60, "Expected 60 distinct hard scenarios")
    require(Counter(c["split"] for c in main_cases) == {"development": 36, "validation": 12, "holdout": 12}, "Hard-case split changed")
    require(all(len(c["prompt"].split()) >= 400 for c in main_cases), "A hard prompt is below the registered length floor")
    records = []
    for filename in evidence["record_files"]:
        records.extend(json.loads(line) for line in (ROOT / filename).read_text(encoding="utf-8").splitlines() if line.strip())
    seen = set()
    for record in records:
        key = (record["variant"], record["case_id"])
        label = "/".join(key)
        require(key not in seen and key[1] in cases, f"Duplicate or unknown record: {label}")
        seen.add(key)
        case = cases[key[1]]
        raw = record["response"].encode("utf-8")
        digest = sha(raw)
        metadata, review = record["metadata"], record["review"]
        require(digest == record["response_sha256"] == metadata["response_sha256"] == review["response_sha256"], f"Response/review hash mismatch: {label}")
        require(len(raw) == metadata["response_bytes"], f"Response byte count mismatch: {label}")
        require(sha(canonical(case)) == metadata["case_sha256"], f"Case changed: {label}")
        require((metadata["variant"], metadata["case_id"]) == key == (review["variant"], review["case_id"]), f"Identity mismatch: {label}")
        require(metadata["status"] == "completed", f"Incomplete generation: {label}")
        require(not record.get("errors"), f"Recorded transport/integrity error: {label}")
        batch = metadata["source_metadata"]
        require(1 <= batch["batch_size"] <= 6 and len(batch["batch_order"]) == batch["batch_size"] and key[1] in batch["batch_order"], f"Invalid batch provenance: {label}")
        require(record["word_count"] == word_count(record["response"]), f"Word count mismatch: {label}")
        require(record["character_count"] == len(record["response"]), f"Character count mismatch: {label}")
        dimensions = review["dimensions"]
        require(set(dimensions) == DIMENSIONS and all(type(v) is int and 0 <= v <= 2 for v in dimensions.values()), f"Invalid dimension scores: {label}")
        require(review["max_score"] == 12 and review["score"] == sum(dimensions.values()), f"Invalid total score: {label}")
        require(review["verdict"] in {"pass", "partial", "fail"}, f"Unknown verdict: {label}")
        require(isinstance(review.get("critical_errors"), list), f"Missing critical-error assessment: {label}")
        if review["critical_errors"] or any(dimensions[k] == 0 for k in ("accuracy", "evidence", "coverage", "fit")):
            require(review["verdict"] == "fail", f"Critical failure hidden by score: {label}")
        if review["verdict"] == "pass":
            require(review["score"] >= 11 and review.get("hard_constraints_satisfied") is True, f"Passing review violates policy: {label}")
            require(review["criteria"] and all(c["verdict"] == "pass" for c in review["criteria"]), f"Passing review has unmet essentials: {label}")
        checks = constraint_checks(record["response"], case["constraints"])
        mechanical_ok = not any(c.get("passed") is False for c in checks)
        require(record["deterministic_pass"] == mechanical_ok, f"Mechanical-check mismatch: {label}")
        require(record["review_state"] == "valid", f"Unbound review: {label}")
        require(record["fully_reviewed_pass"] == (mechanical_ok and review["verdict"] == "pass"), f"Pass flag mismatch: {label}")
        version = evidence["variants"][key[0]]
        require(metadata["skill_sha256"] == version["skill_sha256"], f"Wrong skill version: {label}")
        require(metadata.get("bundle_sha256") == version.get("bundle_sha256"), f"Wrong bundle version: {label}")
    require(len(records) == evidence["actual_responses"], "Recorded response total differs")
    for variant, expected in evidence["summaries"].items():
        selected = [r for r in records if r["variant"] == variant and r["case_id"] in {c["id"] for c in main_cases}]
        observed = stats(selected)
        for field, value in observed.items():
            require(math.isclose(value, expected[field], abs_tol=1e-9), f"Aggregate differs: {variant}/{field}")
    hard_ids = {c["id"] for c in main_cases}
    for variant in (evidence["baseline_variant"], evidence["release_variant"]):
        require({r["case_id"] for r in records if r["variant"] == variant and r["case_id"] in hard_ids} == hard_ids, f"Incomplete 60-case coverage: {variant}")
    release = evidence["variants"][evidence["release_variant"]]
    frozen = ROOT / release["directory"]
    historical = dict(read_runtime_bundle(frozen))
    if require_current:
        actual = dict(read_runtime_bundle(ROOT.parents[1]))
        require(actual == historical, "Current runtime bundle differs from the recorded release")
    return evidence, records


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Print the verified descriptive summaries")
    parser.add_argument("--require-current", action="store_true", help="Also require the current runtime bundle to match the recorded release")
    args = parser.parse_args()
    try:
        evidence, records = verify(require_current=args.require_current)
        if args.json:
            print(json.dumps(evidence["summaries"], indent=2))
        else:
            print(f"Verified {len(records)} archived responses, hashes, reviews, and frozen runtime versions.")
            if args.require_current:
                print("Current runtime bundle matches the recorded release.")
            for variant, summary in evidence["summaries"].items():
                print(f"{variant}: {summary['pass']}/{summary['responses']} pass; {summary['partial']} partial; {summary['fail']} fail.")
            print("No new generation or semantic grading was performed. Exit status checks integrity, not universal explanation quality.")
        return 0
    except (ValueError, KeyError, TypeError, OSError) as error:
        print(f"Advanced reference check failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
