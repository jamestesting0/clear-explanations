#!/usr/bin/env python3
"""Verify the published reference record; optionally render its unchanged answers."""
from __future__ import annotations

import argparse
from collections import Counter
import json
import math
from pathlib import Path
import sys

from core import canonical, constraint_checks, now, sha, validate_cases, word_count
from report import render_report


def require(condition, message):
    if not condition:
        raise ValueError(message)


def verify():
    evaluation = Path(__file__).resolve().parents[1]
    repo = evaluation.parent
    evidence = json.loads((evaluation / "evidence.json").read_text(encoding="utf-8"))
    cases = {c["id"]: c for c in validate_cases(json.loads((evaluation / "cases.json").read_text(encoding="utf-8")))}
    records = [json.loads(line) for line in (evaluation / "results.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    require(evidence["schema_version"] == 1, "Unsupported evidence schema")
    for name, digest in evidence["recorded_files_sha256"].items():
        require(sha((evaluation / name).read_bytes()) == digest, f"Recorded file changed: {name}")
    require(sha((repo / "SKILL.md").read_bytes()) == evidence["skill_sha256"], "Current skill differs from the recorded release")
    frozen = evaluation / evidence["files"]["frozen_final_skill"]
    require(frozen.read_bytes() == (repo / "SKILL.md").read_bytes(), "Frozen release and current skill differ")
    require(len(records) == evidence["actual_responses"], "Response count differs from summary")
    seen = set()
    for record in records:
        key = (record["variant"], record["case_id"])
        label = "/".join(key)
        require(key not in seen, f"Duplicate record: {label}")
        seen.add(key)
        require(record["case_id"] in cases, f"Unknown scenario: {label}")
        case = cases[record["case_id"]]
        raw = record["response"].encode("utf-8")
        digest = sha(raw)
        review, metadata = record["review"], record["metadata"]
        require(digest == record["response_sha256"] == review["response_sha256"] == metadata["response_sha256"], f"Response or review hash mismatch: {label}")
        require(len(raw) == metadata["response_bytes"], f"Response byte count changed: {label}")
        require(sha(canonical(case)) == metadata["case_sha256"], f"Case changed: {label}")
        require(word_count(record["response"]) == record["word_count"], f"Word count changed: {label}")
        checks = constraint_checks(record["response"], case.get("constraints", {}))
        require(not any(c.get("passed") is False for c in checks), f"Deterministic constraint failed: {label}")
        require(record["deterministic_pass"] is True, f"Reference has a recorded integrity failure: {label}")
        require(record["review_state"] == "valid", f"Reference lacks a valid stored review: {label}")
        require(review["variant"] == record["variant"] and review["case_id"] == record["case_id"], f"Review identifies another record: {label}")
        require(review["verdict"] in {"pass", "partial", "fail"}, f"Unknown review verdict: {label}")
        require(review["max_score"] == 10 and 0 <= review["score"] <= 10, f"Invalid review score: {label}")
        require(review["verdict"] != "pass" or review["score"] >= 9, f"Passing score below registered threshold: {label}")
        require(record["fully_reviewed_pass"] == (review["verdict"] == "pass"), f"Pass summary mismatch: {label}")
    unique = {r["case_id"] for r in records}
    final = [r for r in records if r["variant"] == evidence["release"]]
    require(len(unique) == evidence["unique_scenarios"] == len(cases), "Unique scenario count differs")
    require({r["case_id"] for r in final} == set(cases), "Final release does not cover every scenario")
    require(len(final) == evidence["final_responses"], "Final response count differs")
    require(sum(r["fully_reviewed_pass"] for r in final) == evidence["final_pass"], "Final pass count differs")
    for variant, summary in evidence["historical_drafts"].items():
        selected = [r for r in records if r["variant"] == variant]
        counts = Counter(r["review"]["verdict"] for r in selected)
        require(len(selected) == summary["responses"], f"Draft response count differs: {variant}")
        for verdict in ["pass", "partial", "fail"]:
            require(counts[verdict] == summary[verdict], f"Draft verdict count differs: {variant}/{verdict}")
    for variant, summary in evidence["natural_comparison"].items():
        selected = [r for r in records if r["variant"] == variant and r["case_id"].startswith("N")]
        require(len(selected) == summary["cases"], f"Comparison coverage differs: {variant}")
        require(sum(r["fully_reviewed_pass"] for r in selected) == summary["pass"], f"Comparison pass count differs: {variant}")
        for field, mean in [("mean_words", sum(r["word_count"] for r in selected) / len(selected)),
                            ("mean_score", sum(r["review"]["score"] for r in selected) / len(selected))]:
            require(math.isclose(mean, summary[field], abs_tol=1e-9), f"Comparison mean differs: {variant}/{field}")
    return evidence, cases, records


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, help="Write a local HTML view after successful integrity checks")
    args = parser.parse_args()
    try:
        evidence, cases, records = verify()
        print(f"Verified {len(records)} response hashes and reviews across {len(cases)} scenarios.")
        print(f"Recorded {evidence['release']} outcome: {evidence['final_pass']}/{evidence['final_responses']} pass.")
        print("No new model generation or semantic grading was performed.")
        if args.report:
            result = {
                "schema_version": 1,
                "generated_at": now(),
                "run_name": "Clear Explanations: recorded evaluation",
                "review_provenance": {
                    "method": "Stored independent model reviews; hashes and deterministic constraints rechecked locally.",
                    "holdout_note": "Split labels are historical. All final v4 cases are regression cases after prior inspection.",
                    "publication_note": evidence["publication_note"],
                    "limits": evidence["limits"],
                },
                "results": [{**r, "case": cases[r["case_id"]], "errors": []} for r in records],
            }
            args.report.parent.mkdir(parents=True, exist_ok=True)
            args.report.write_text(render_report(result), encoding="utf-8")
            print(f"Wrote {args.report}")
        return 0
    except (ValueError, KeyError, TypeError, OSError) as error:
        print(f"Reference check failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
