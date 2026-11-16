#!/usr/bin/env python3
"""Verify archived inputs, outcomes, and descriptive arithmetic; never grade answers.

Advanced archives use schema_version 1 with integrity_version 2. A successful
check establishes consistency of the declared archive, not reviewer correctness,
model compliance, unseen status, or a quality pass. Original reviews and gold
remain unchanged; reporting_verdict applies registered hard-failure overrides.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
import math
from pathlib import Path, PurePosixPath
import re
import stat
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent / "tools"))
from core import (BUNDLE_MODE, bundle_digest, canonical, constraint_checks, format_packet,
                  read_runtime_bundle, runtime_resource_name, sha, valid_id, validate_cases,
                  validate_reviews, word_count)

DIMENSIONS = {"accuracy", "evidence", "coverage", "clarity", "structure", "fit"}
CRITICAL_DIMENSIONS = {"accuracy", "evidence", "coverage", "fit"}
SPLITS = ("development", "validation", "holdout")
SHORT_IDS = {f"N{number:02d}" for number in range(1, 7)}
INPUT_NAMES = {"protocol", "protocol_addendum", "short_transfer_plan", "generation_instructions", "review_instructions"}
HASH = re.compile(r"[a-f0-9]{64}\Z")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read_json(path):
    return json.loads(path.read_bytes())


def unique_strings(value, label, nonempty=True):
    require(isinstance(value, list) and (bool(value) or not nonempty)
            and all(isinstance(item, str) and item.strip() for item in value), f"Invalid {label}")
    require(len(value) == len(set(value)), f"Duplicate {label}")
    return value


class Archive:
    """Every consumed file must be explicitly hashed and contained in the archive."""
    def __init__(self, root, inventory):
        self.root = Path(root).resolve()
        require(isinstance(inventory, dict) and inventory, "Recorded file hash inventory must be nonempty")
        self.inventory, self.contents, self.documents = inventory, {}, {}
        for name, digest in inventory.items():
            require(isinstance(digest, str) and HASH.fullmatch(digest), f"Invalid recorded digest: {name}")
            path = self.path(name)
            require(stat.S_ISREG(path.lstat().st_mode), f"Recorded resource is not a regular file: {name}")
            raw = path.read_bytes()
            require(sha(raw) == digest, f"Recorded file changed: {name}")
            self.contents[name] = raw

    def path(self, name):
        require(isinstance(name, str) and name and "\\" not in name, f"Invalid archive path: {name!r}")
        relative = PurePosixPath(name)
        require(not relative.is_absolute() and relative.as_posix() == name and ".." not in relative.parts
                and name != ".", f"Archive path escapes or is not normalized: {name!r}")
        path = self.root.joinpath(*relative.parts)
        require(self.root in path.resolve().parents, f"Archive path escapes archive: {name}")
        require(not any(part.is_symlink() for part in (path, *path.parents) if part != self.root and self.root in part.parents),
                f"Archive path traverses a symlink: {name}")
        return path

    def raw(self, name):
        require(isinstance(name, str) and name in self.contents, f"Consumed file is missing from hash inventory: {name}")
        return self.contents[name]

    def json(self, name):
        if name not in self.documents:
            self.documents[name] = json.loads(self.raw(name))
        return self.documents[name]


def hard_failure(record):
    return record["deterministic_pass"] is False or record["review"]["hard_constraints_satisfied"] is False


def critical_failure(record):
    review = record["review"]
    return hard_failure(record) or bool(review["critical_errors"]) or any(review["dimensions"][key] == 0 for key in CRITICAL_DIMENSIONS)


def resolved_verdict(record):
    """Apply registered failures without editing the preserved reviewer judgment."""
    return "fail" if critical_failure(record) else record["review"]["verdict"]


def stats(records):
    require(bool(records), "Cannot summarize an empty group")
    verdicts = Counter(record["reporting_verdict"] for record in records)
    require(sum(verdicts[key] for key in ("pass", "partial", "fail")) == len(records), "Verdicts do not partition responses")
    return {"responses": len(records), "pass": verdicts["pass"], "partial": verdicts["partial"], "fail": verdicts["fail"],
            "critical_failures": sum(critical_failure(record) for record in records),
            "hard_constraint_failures": sum(hard_failure(record) for record in records),
            "mean_words": sum(record["word_count"] for record in records) / len(records),
            "mean_characters": sum(len(record["response"]) for record in records) / len(records),
            "mean_score": sum(record["review"]["score"] for record in records) / len(records),
            "mean_dimensions": {key: sum(record["review"]["dimensions"][key] for record in records) / len(records)
                                for key in sorted(DIMENSIONS)}}


def paired_stats(baseline, release):
    """Release-minus-baseline arithmetic; verdict rank and score comparisons stay distinct."""
    left, right = ({record["case_id"]: record for record in records} for records in (baseline, release))
    require(left and set(left) == set(right) and len(left) == len(baseline) and len(right) == len(release),
            "Paired summaries require one record per identical case set")
    pairs = [(left[case_id], right[case_id]) for case_id in sorted(left)]
    rank = {"fail": 0, "partial": 1, "pass": 2}
    def comparisons(values):
        return {"wins": sum(value > 0 for value in values), "ties": sum(value == 0 for value in values),
                "regressions": sum(value < 0 for value in values)}
    return {"pairs": len(pairs),
            "verdict_comparison": comparisons([rank[b["reporting_verdict"]] - rank[a["reporting_verdict"]] for a, b in pairs]),
            "score_comparison": comparisons([b["review"]["score"] - a["review"]["score"] for a, b in pairs]),
            "mean_score_delta": sum(b["review"]["score"] - a["review"]["score"] for a, b in pairs) / len(pairs),
            "mean_words_delta": sum(b["word_count"] - a["word_count"] for a, b in pairs) / len(pairs),
            "mean_characters_delta": sum(len(b["response"]) - len(a["response"]) for a, b in pairs) / len(pairs),
            "mean_dimension_deltas": {key: sum(b["review"]["dimensions"][key] - a["review"]["dimensions"][key]
                                               for a, b in pairs) / len(pairs) for key in sorted(DIMENSIONS)}}


def compare_summary(expected, observed, label):
    if isinstance(observed, dict):
        require(isinstance(expected, dict) and set(expected) == set(observed), f"Missing or unchecked aggregate fields: {label}")
        for key in observed:
            compare_summary(expected[key], observed[key], f"{label}/{key}")
    elif type(observed) is int:
        require(type(expected) is int and expected == observed, f"Aggregate differs: {label}")
    else:
        require(type(expected) in {int, float} and math.isfinite(expected)
                and math.isclose(expected, observed, rel_tol=0, abs_tol=1e-9), f"Aggregate differs: {label}")


def checked_inputs(archive, evidence):
    inputs = evidence["inputs"]
    require(isinstance(inputs, dict) and set(inputs) == INPUT_NAMES, "Missing or unknown required archive inputs")
    require(len(set(inputs.values())) == len(inputs), "Required input paths collide")
    for path in inputs.values():
        archive.raw(path)
    protocol = archive.json(inputs["protocol"])
    plan = protocol["case_plan"]
    require(protocol["schema_version"] == 1 and {key: plan[key] for key in ("total", *SPLITS)}
            == {"total": 60, "development": 36, "validation": 12, "holdout": 12}, "Registered case plan differs")
    require(plan["minimum_prompt_whitespace_words"] == 400 and protocol["verdict_policy"]["maximum_score"] == 12,
            "Registered length floor or scoring scale differs")
    require(archive.json(inputs["protocol_addendum"])["schema_version"] == 1, "Unsupported protocol addendum")
    short_plan = archive.json(inputs["short_transfer_plan"])
    require(set(unique_strings(short_plan["case_ids"], "registered short IDs")) == SHORT_IDS, "Registered short cases differ")
    return inputs


def read_archive_bundle(archive, version):
    """Archived INSTRUCTIONS.md may stand for canonical SKILL.md; bytes never change."""
    directory, entry = version["directory"], version.get("entry_file", "SKILL.md")
    require(entry in {"SKILL.md", "INSTRUCTIONS.md"}, "Unsupported archived entry filename")
    root = archive.path(directory)
    require(root.is_dir(), f"Frozen variant directory is missing: {directory}")
    if entry == "INSTRUCTIONS.md":
        require(not (root / "SKILL.md").exists(), f"Ambiguous archived entry files: {directory}")
    selected = [("SKILL.md", f"{directory}/{entry}")]
    references = archive.path(f"{directory}/references")
    if references.exists():
        require(references.is_dir(), f"Invalid frozen references directory: {directory}")
        selected.extend((f"references/{path.name}", f"{directory}/references/{path.name}")
                        for path in references.iterdir() if path.name.lower().endswith(".md"))
    values, seen = {}, set()
    for relative, path in sorted(selected):
        runtime_resource_name(relative)
        require(relative.casefold() not in seen, f"Frozen resource collision: {relative}")
        seen.add(relative.casefold())
        raw = archive.raw(path)
        raw.decode("utf-8")
        values[relative] = raw
    return values


def frozen_versions(archive, evidence):
    variants = evidence["variants"]
    require(isinstance(variants, dict) and variants, "No frozen variants")
    resources = {}
    for name, version in variants.items():
        valid_id(name)
        values = read_archive_bundle(archive, version)
        require(sha(values["SKILL.md"]) == version["skill_sha256"], f"Frozen skill hash mismatch: {name}")
        mode = version["guidance_mode"]
        require(mode in {"single_file", BUNDLE_MODE}, f"Unsupported frozen guidance mode: {name}")
        if mode == BUNDLE_MODE:
            manifest = [{"resource_path": path, "sha256": sha(raw), "bytes": len(raw)} for path, raw in values.items()]
            require(bundle_digest(manifest) == version["bundle_sha256"], f"Frozen bundle hash mismatch: {name}")
        else:
            require(version.get("bundle_sha256") is None and set(values) == {"SKILL.md"}, f"Invalid single-file variant: {name}")
        resources[name] = values
    return resources


def checked_gold(archive, evidence, cases, hard_ids):
    paths = evidence["gold_files"]
    require(isinstance(paths, dict) and set(paths) == {*SPLITS, "short"}, "Missing phase gold inputs")
    require(len(set(paths.values())) == len(paths), "Phase gold paths collide")
    entries = {}
    for phase, path in paths.items():
        gold = archive.json(path)
        expected = {case_id for case_id, case in cases.items()
                    if (case["split"] == phase and case_id in hard_ids) or (phase == "short" and case_id in SHORT_IDS)}
        require(isinstance(gold, dict) and set(gold) == expected, f"Gold case coverage differs: {phase}")
        for case_id, entry in gold.items():
            essentials = entry["must_include"]
            require(isinstance(essentials, list) and essentials and all(isinstance(item, str) and item.strip() for item in essentials),
                    f"Missing gold essential criteria: {case_id}")
            entries[case_id] = (path, {f"C{index}" for index in range(1, len(essentials) + 1)})
    return entries


def checked_batches(archive, evidence, cases, packet_hashes):
    document = archive.json(evidence["batches_file"])
    require(document.get("schema_version") == 1 and isinstance(document.get("batches"), list) and document["batches"], "Invalid batch archive")
    batches, members = {}, {}
    instructions_hash = sha(archive.raw(evidence["inputs"]["generation_instructions"]))
    for batch in document["batches"]:
        require(isinstance(batch["batch_id"], str) and batch["batch_id"].strip(), "Missing batch identity")
        key = (valid_id(batch["variant"]), batch["batch_id"])
        require(key not in batches and key[0] in evidence["variants"], f"Duplicate or unknown batch: {key}")
        order = unique_strings(batch["batch_order"], "ordered batch case IDs")
        require(type(batch["batch_size"]) is int and 1 <= batch["batch_size"] <= 6 and len(order) == batch["batch_size"], f"Invalid batch size: {key}")
        require(set(order).issubset(cases), f"Unknown batch case: {key}")
        descriptor = [{"case_id": case_id, "prompt_sha256": packet_hashes[(key[0], case_id)]} for case_id in order]
        require(sha(canonical(descriptor)) == batch["ordered_batch_sha256"], f"Ordered batch hash mismatch: {key}")
        require(batch["generation_instructions_sha256"] == instructions_hash, f"Generation instruction hash mismatch: {key}")
        runtime_file, runtime_hash = batch.get("runtime_prompt_file"), batch.get("runtime_prompt_sha256")
        require("runtime_prompt_file" in batch and "runtime_prompt_sha256" in batch, f"Missing runtime-context disclosure: {key}")
        if runtime_file is None:
            require(runtime_hash is None, f"Unsupported claimed full runtime prompt hash: {key}")
        else:
            require(sha(archive.raw(runtime_file)) == runtime_hash, f"Full runtime prompt hash mismatch: {key}")
        for case_id in order:
            identity = (key[0], case_id)
            require(identity not in members, f"Case appears in multiple batches: {identity}")
            members[identity] = batch
        batches[key] = batch
    baseline, release = evidence["baseline_variant"], evidence["release_variant"]
    baseline_orders = {tuple(batch["batch_order"]) for (variant, _), batch in batches.items() if variant == baseline}
    release_orders = {tuple(batch["batch_order"]) for (variant, _), batch in batches.items() if variant == release}
    require(baseline_orders == release_orders, "Compared variants have different batch membership or order")
    return members


def checked_review_binding(archive, evidence, record, case, gold, reviews):
    label = f"{record['variant']}/{record['case_id']}"
    provenance = record["review_provenance"]
    source = provenance["review_file"]
    require(source in reviews and provenance["review_file_sha256"] == sha(archive.raw(source)), f"Unbound review source: {label}")
    key = (record["variant"], record["case_id"])
    require(key in reviews[source] and reviews[source][key] == record["review"], f"Final review differs from its preserved source: {label}")
    case_hash, prompt_hash = sha(canonical(case)), sha(case["prompt"].encode("utf-8"))
    require((provenance["case_sha256"], provenance["user_prompt_sha256"], provenance["response_sha256"])
            == (case_hash, prompt_hash, record["response_sha256"]), f"Reviewed case/prompt/response binding mismatch: {label}")
    packet_path, index_path = provenance["review_packet_file"], provenance["review_index_file"]
    packet_raw, index_raw = archive.raw(packet_path), archive.raw(index_path)
    require(sha(packet_raw) == provenance["review_packet_sha256"] and sha(index_raw) == provenance["review_index_sha256"],
            f"Reviewed packet/index hash mismatch: {label}")
    packet, index = archive.json(packet_path), archive.json(index_path)
    require(packet.get("schema_version") == 1 and packet.get("review_id") == provenance["review_id"]
            and packet.get("case_id") == record["case_id"] and packet.get("case_sha256") == case_hash
            and packet.get("prompt") == case["prompt"] and packet.get("constraints") == case["constraints"]
            and packet.get("response") == record["response"] and packet.get("response_sha256") == record["response_sha256"],
            f"Reviewed packet content differs: {label}")
    require(index.get("schema_version") == 1 and index.get("kind") == "blind-review-packets", f"Invalid blind review index: {label}")
    descriptors = index["packets"]
    require(isinstance(descriptors, list) and len({item["review_id"] for item in descriptors}) == len(descriptors),
            f"Duplicate blind review packet ID: {label}")
    selected = [item for item in descriptors if item["review_id"] == provenance["review_id"]]
    require(len(selected) == 1, f"Reviewed packet missing from index: {label}")
    parent = PurePosixPath(index_path).parent
    for descriptor in descriptors:
        path = (parent / descriptor["packet_path"]).as_posix()
        require(sha(archive.raw(path)) == descriptor["packet_sha256"], f"Blind index contains an unbound packet: {label}")
    descriptor = selected[0]
    require((parent / descriptor["packet_path"]).as_posix() == packet_path
            and descriptor["packet_sha256"] == provenance["review_packet_sha256"] and descriptor["case_id"] == record["case_id"],
            f"Blind index identifies a different packet: {label}")
    gold_path, expected_criteria = gold[record["case_id"]]
    gold_hash = sha(archive.raw(gold_path))
    copied_gold = (parent / index["rubric_path"]).as_posix()
    require(index["rubric_sha256"] == gold_hash == sha(archive.raw(copied_gold)), f"Blind review used different gold: {label}")
    annotation_paths = unique_strings(provenance.get("gold_annotation_files", []), "applied gold annotations", nonempty=False)
    require(set(annotation_paths).issubset(evidence.get("gold_annotation_files", [])), f"Undeclared gold annotations: {label}")
    inputs = evidence["inputs"]
    expected_inputs = {path: sha(archive.raw(path)) for path in
                       [inputs["protocol"], inputs["protocol_addendum"], inputs["review_instructions"], gold_path, *annotation_paths]}
    require(provenance["input_files_sha256"] == expected_inputs, f"Review protocol/instructions/gold binding mismatch: {label}")
    criteria = record["review"]["criteria"]
    require(isinstance(criteria, list) and len(criteria) == len(expected_criteria)
            and {item["criterion"] for item in criteria} == expected_criteria, f"Missing, duplicate, or unknown essential review criteria: {label}")


def verify(require_current=False):
    evidence = read_json(ROOT / "evidence.json")
    require(evidence.get("schema_version") == 1 and evidence.get("integrity_version") == 2, "Unsupported advanced archive integrity schema")
    archive = Archive(ROOT, evidence["recorded_files_sha256"])
    checked_inputs(archive, evidence)
    resources = frozen_versions(archive, evidence)
    for field in ("gold_annotation_files", "provenance_files"):
        for path in unique_strings(evidence.get(field, []), field, nonempty=False):
            archive.raw(path)
    main_cases = validate_cases(archive.json("cases.json"))
    short_cases = validate_cases(archive.json("short-cases.json"))
    cases = {case["id"]: case for case in main_cases + short_cases}
    require(len(cases) == len(main_cases) + len(short_cases), "Duplicate hard/short case ID")
    hard_ids = {case["id"] for case in main_cases}
    require(len(main_cases) == 60 and Counter(case["split"] for case in main_cases)
            == {"development": 36, "validation": 12, "holdout": 12}, "Expected 60 hard cases with registered splits")
    require(all(len(case["prompt"].split()) >= 400 for case in main_cases), "A hard prompt is below the registered length floor")
    require({case["id"] for case in short_cases} == SHORT_IDS and len(short_cases) == 6, "Expected registered short cases N01–N06")
    gold = checked_gold(archive, evidence, cases, hard_ids)
    baseline, release = evidence["baseline_variant"], evidence["release_variant"]
    require(baseline != release and {baseline, release}.issubset(resources), "Invalid compared final variants")
    coverage = evidence["variant_case_ids"]
    require(isinstance(coverage, dict) and set(coverage) == set(resources), "Variant coverage declarations differ from frozen variants")
    for variant, ids in coverage.items():
        require(set(unique_strings(ids, f"scheduled cases for {variant}")).issubset(cases), f"Unknown scheduled case: {variant}")
    for variant in (baseline, release):
        require(set(coverage[variant]) == set(cases), f"Compared final variant lacks 60 hard plus 6 short cases: {variant}")
    packet_hashes = {}
    for variant, values in resources.items():
        bundled = evidence["variants"][variant]["guidance_mode"] == BUNDLE_MODE
        for case_id, case in cases.items():
            packet = format_packet(case, resources=list(values.items())) if bundled else format_packet(case, skill=values["SKILL.md"])
            packet_hashes[(variant, case_id)] = sha(packet)
    members = checked_batches(archive, evidence, cases, packet_hashes)
    reviews = {}
    for path in unique_strings(evidence["review_files"], "review source files"):
        reviews[path] = validate_reviews(archive.json(path))
    records = []
    for filename in unique_strings(evidence["record_files"], "record files"):
        records.extend(json.loads(line) for line in archive.raw(filename).decode("utf-8").splitlines() if line.strip())
    require(records and len(records) == evidence["actual_responses"], "Recorded response total differs or is empty")
    seen = set()
    for record in records:
        key = (valid_id(record["variant"]), valid_id(record["case_id"]))
        label = "/".join(key)
        require(key not in seen and key[1] in cases and key[0] in resources, f"Duplicate or unknown record: {label}")
        seen.add(key)
        case = cases[key[1]]
        require(isinstance(record["response"], str) and record["response"].strip(), f"Missing response: {label}")
        raw = record["response"].encode("utf-8")
        digest = sha(raw)
        metadata, review = record["metadata"], record["review"]
        require(digest == record["response_sha256"] == metadata["response_sha256"] == review["response_sha256"], f"Response/review hash mismatch: {label}")
        require(len(raw) == metadata["response_bytes"], f"Response byte count mismatch: {label}")
        require(sha(canonical(case)) == metadata["case_sha256"], f"Case changed: {label}")
        require((metadata["variant"], metadata["case_id"]) == key == (review["variant"], review["case_id"]), f"Identity mismatch: {label}")
        require(metadata["status"] == "completed" and not record.get("errors"), f"Incomplete generation or recorded integrity error: {label}")
        require(metadata["prompt_sha256_role"] == "canonical_replay_packet"
                and metadata["prompt_sha256"] == packet_hashes[key], f"Canonical replay prompt hash/role mismatch: {label}")
        version = evidence["variants"][key[0]]
        require(metadata["skill_sha256"] == version["skill_sha256"] and metadata.get("bundle_sha256") == version.get("bundle_sha256"),
                f"Wrong frozen guidance version: {label}")
        require(metadata.get("guidance_mode", "single_file") == version["guidance_mode"], f"Wrong guidance mode: {label}")
        require(key in members, f"Record has no ordered batch: {label}")
        batch, declared = members[key], metadata["source_metadata"]
        for field in ("batch_id", "batch_order", "batch_size", "ordered_batch_sha256"):
            require(declared[field] == batch[field], f"Inconsistent batch {field}: {label}")
        require("runtime_prompt_sha256" in metadata and metadata["runtime_prompt_sha256"] == batch["runtime_prompt_sha256"],
                f"Unsupported or inconsistent full runtime prompt hash: {label}")
        if "runtime_prompt_sha256" in declared:
            require(declared["runtime_prompt_sha256"] == metadata["runtime_prompt_sha256"], f"Conflicting runtime prompt hash: {label}")
        require(record["word_count"] == word_count(record["response"]) and record["character_count"] == len(record["response"]),
                f"Response length summary mismatch: {label}")
        dimensions = review["dimensions"]
        require(set(dimensions) == DIMENSIONS and all(type(value) is int and 0 <= value <= 2 for value in dimensions.values()), f"Invalid dimension scores: {label}")
        require(review["max_score"] == 12 and review["score"] == sum(dimensions.values()), f"Invalid total score: {label}")
        require(review["verdict"] in {"pass", "partial", "fail"} and type(review["hard_constraints_satisfied"]) is bool
                and isinstance(review["critical_errors"], list) and isinstance(review["gold_flags"], list), f"Missing or invalid review assessments: {label}")
        checked_review_binding(archive, evidence, record, case, gold, reviews)
        mechanical_ok = not any(check.get("passed") is False for check in constraint_checks(record["response"], case["constraints"]))
        require(record["deterministic_pass"] is mechanical_ok, f"Mechanical-check mismatch: {label}")
        outcome = resolved_verdict(record)
        require(record["reporting_verdict"] == outcome, f"Hard/critical failure missing from reporting verdict: {label}")
        if outcome == "pass":
            require(review["score"] >= 11 and all(item["verdict"] == "pass" for item in review["criteria"]), f"Passing review violates score/essential gates: {label}")
        require(record["review_state"] == "valid", f"Unbound review state: {label}")
        require(record["fully_reviewed_pass"] is (outcome == "pass"), f"Pass flag mismatch: {label}")
    scheduled = {(variant, case_id) for variant, ids in coverage.items() for case_id in ids}
    require(seen == scheduled == set(members), "Record, scheduled coverage, and ordered batch membership differ")
    hard_groups = {variant: [record for record in records if record["variant"] == variant and record["case_id"] in hard_ids]
                   for variant in coverage}
    short_groups = {variant: [record for record in records if record["variant"] == variant and record["case_id"] in SHORT_IDS]
                    for variant in coverage}
    hard_summaries = {variant: stats(group) for variant, group in hard_groups.items() if group}
    short_summaries = {variant: stats(group) for variant, group in short_groups.items() if group}
    splits = {variant: {split: stats(selected) for split in SPLITS
                        if (selected := [record for record in group if cases[record["case_id"]]["split"] == split])}
              for variant, group in hard_groups.items() if group}
    pairs = {"hard": paired_stats(hard_groups[baseline], hard_groups[release]),
             "short": paired_stats(short_groups[baseline], short_groups[release]),
             "by_split": {split: paired_stats([record for record in hard_groups[baseline] if cases[record["case_id"]]["split"] == split],
                                              [record for record in hard_groups[release] if cases[record["case_id"]]["split"] == split]) for split in SPLITS}}
    for field, observed in (("summaries", hard_summaries), ("short_summaries", short_summaries),
                            ("split_summaries", splits), ("paired_summary", pairs)):
        compare_summary(evidence[field], observed, field)
    if require_current:
        actual = dict(read_runtime_bundle(ROOT.parents[1]))
        require(actual == resources[release], "Current runtime bundle differs from the recorded release")
    return evidence, records


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Print only verified hard/short, split, and paired descriptive summaries")
    parser.add_argument("--require-current", action="store_true", help="Also require the current runtime bundle to match the recorded release")
    args = parser.parse_args(argv)
    try:
        evidence, records = verify(require_current=args.require_current)
        if args.json:
            print(json.dumps({field: evidence[field] for field in ("summaries", "short_summaries", "split_summaries", "paired_summary")}, indent=2))
        else:
            print(f"Verified {len(records)} archived responses, declared input bindings, reporting outcomes, and frozen runtime versions.")
            if args.require_current:
                print("Current runtime bundle matches the recorded release.")
            for field, label in (("summaries", "hard"), ("short_summaries", "short")):
                for variant, summary in evidence[field].items():
                    print(f"{variant} ({label}): {summary['pass']}/{summary['responses']} pass; {summary['partial']} partial; {summary['fail']} fail.")
            print("No new generation or semantic grading was performed. Exit status checks integrity, not universal explanation quality.")
        return 0
    except (ValueError, KeyError, TypeError, OSError, AttributeError) as error:
        print(f"Advanced reference check failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
