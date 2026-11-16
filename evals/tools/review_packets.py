"""Prepare blinded reviewer inputs and bind completed judgments back to exact runs.

No model, reviewer, or semantic scoring rule is invoked here. Only the reviewer
directory should be shared with a reviewer; its identity key stays separate.
Blinding removes variant/provenance labels, not clues inside an answer itself.
"""
from __future__ import annotations

import json
from pathlib import Path
import random

from core import SCHEMA, canonical, evaluate_many, now, read_json, sha, validate_reviews, within


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def write_new(path, raw):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        handle.write(raw)


def separate_key(directory, key):
    directory, key = Path(directory).resolve(), Path(key).resolve()
    if key == directory or directory in key.parents:
        raise ValueError("The private --key must be outside the reviewer --out/--packets directory")
    return directory, key


def current_records(runs):
    result = evaluate_many(runs)
    invalid = [f"{record['variant']}/{record['case_id']}" for record in result["results"] if record["errors"]]
    if invalid:
        raise ValueError("Blind review requires complete, unaltered, successfully collected responses: "
                         + ", ".join(invalid))
    return result


def make_review_packets(args):
    """Export exact response strings, with shuffled anonymous IDs within each case."""
    directory, key_path = separate_key(args.out, args.key)
    if (directory.exists() and (not directory.is_dir() or any(directory.iterdir()))) or key_path.exists():
        raise ValueError("Reviewer directory must be new/empty and private key must be new")
    result = current_records(args.run)
    files, rubric_fields = {}, {}
    if args.rubric:
        rubric = Path(args.rubric).read_bytes()
        json.loads(rubric.decode("utf-8"))
        files["rubric.json"] = rubric
        rubric_fields = {"rubric_path": "rubric.json", "rubric_sha256": sha(rubric)}
    index = {"schema_version": SCHEMA, "kind": "blind-review-packets", "created_at": now(),
             "note": "Review scores are separate judgments, not mechanical checks. Same case IDs have identical "
                     "case snapshots. Anonymous order is shuffled within each case. No independent review is "
                     "implied by preparing these files; answer text may contain identity clues.",
             "packets": [], **rubric_fields}
    template = {"schema_version": SCHEMA, "reviewer": "REPLACE_WITH_REVIEWER_AND_METHOD", "reviews": []}
    mapping = []
    grouped = {}
    for record in result["results"]:
        grouped.setdefault(record["case_id"], []).append(record)
    generator = random.SystemRandom()
    for case_id in sorted(grouped):
        records = sorted(grouped[case_id], key=lambda record: record["variant"])
        generator.shuffle(records)
        for record in records:
            review_id = f"REVIEW-{len(mapping) + 1:04d}"
            case_hash = sha(canonical(record["case"]))
            packet = {"schema_version": SCHEMA, "review_id": review_id, "case_id": case_id,
                      "case_sha256": case_hash, "prompt": record["case"]["prompt"],
                      "constraints": record["case"]["constraints"], "response": record["response"],
                      "response_sha256": record["response_sha256"]}
            packet_path = f"packets/{review_id}.json"
            files[packet_path] = json_bytes(packet)
            index["packets"].append({"review_id": review_id, "case_id": case_id,
                                     "packet_path": packet_path, "packet_sha256": sha(files[packet_path])})
            mapping.append({"review_id": review_id, "variant": record["variant"], "case_id": case_id,
                            "case_sha256": case_hash, "response_sha256": record["response_sha256"]})
            template["reviews"].append({"review_id": review_id, "response_sha256": record["response_sha256"],
                                        "verdict": "UNREVIEWED", "rationale": "", "criteria": []})
    files["index.json"] = json_bytes(index)
    files["review-template.json"] = json_bytes(template)
    key = {"schema_version": SCHEMA, "kind": "private-blind-review-key", "created_at": now(),
           "review_index_sha256": sha(files["index.json"]),
           "scheduled_runs": result["review_provenance"]["scheduled_runs"], "entries": mapping}
    for relative, raw in files.items():
        write_new(directory / relative, raw)
    write_new(key_path, json_bytes(key))
    print(f"Wrote {len(mapping)} blind reviewer packets to {directory}")
    print(f"Keep private identity key separate: {key_path}")
    print("UNREVIEWED entries are invalid until completed by a separate reviewer.")


def import_blind_reviews(args):
    """Validate the original review inputs and current runs before resolving aliases."""
    directory, key_path = separate_key(args.packets, args.key)
    destination = Path(args.out)
    if destination.exists():
        raise ValueError("Completed review destination already exists")
    key = read_json(key_path)
    if (not isinstance(key, dict) or key.get("schema_version") != SCHEMA
            or key.get("kind") != "private-blind-review-key" or not isinstance(key.get("entries"), list)):
        raise ValueError("Invalid private blind review key")
    index_raw = (directory / "index.json").read_bytes()
    if sha(index_raw) != key.get("review_index_sha256"):
        raise ValueError("Blind reviewer packet index hash mismatch")
    index = json.loads(index_raw)
    if (not isinstance(index, dict) or index.get("schema_version") != SCHEMA
            or index.get("kind") != "blind-review-packets" or not isinstance(index.get("packets"), list)):
        raise ValueError("Invalid blind reviewer packet index")
    if "rubric_path" in index:
        if index["rubric_path"] != "rubric.json" or sha((directory / "rubric.json").read_bytes()) != index.get("rubric_sha256"):
            raise ValueError("Blind reviewer rubric hash mismatch")
    result = current_records(args.run)
    source_hashes = sorted(source["index_sha256"] for source in result["review_provenance"]["scheduled_runs"])
    if source_hashes != sorted(source["index_sha256"] for source in key["scheduled_runs"]):
        raise ValueError("Blind review key identifies different scheduled runs")
    records = {(record["variant"], record["case_id"]): record for record in result["results"]}
    mapping, identities = {}, set()
    for entry in key["entries"]:
        review_id = entry["review_id"]
        identity = (entry["variant"], entry["case_id"])
        if review_id in mapping or identity in identities or identity not in records:
            raise ValueError("Duplicate or unknown identity in blind review key")
        record = records[identity]
        if (entry["response_sha256"] != record["response_sha256"]
                or entry["case_sha256"] != sha(canonical(record["case"]))):
            raise ValueError("Blind review key has a stale response or case hash")
        mapping[review_id] = entry
        identities.add(identity)
    if identities != set(records):
        raise ValueError("Blind review key does not cover the scheduled responses")
    seen_packets = set()
    for descriptor in index["packets"]:
        review_id = descriptor["review_id"]
        if review_id in seen_packets or review_id not in mapping or descriptor["packet_path"] != f"packets/{review_id}.json":
            raise ValueError("Duplicate or unknown blind reviewer packet")
        raw = within(directory, descriptor["packet_path"]).read_bytes()
        if sha(raw) != descriptor["packet_sha256"]:
            raise ValueError(f"Blind reviewer packet hash mismatch: {review_id}")
        packet, entry = json.loads(raw), mapping[review_id]
        record = records[(entry["variant"], entry["case_id"])]
        if (packet.get("review_id") != review_id or packet.get("case_id") != entry["case_id"]
                or descriptor["case_id"] != entry["case_id"] or packet.get("case_sha256") != entry["case_sha256"]
                or packet.get("prompt") != record["case"]["prompt"]
                or packet.get("constraints") != record["case"]["constraints"]
                or packet.get("response_sha256") != entry["response_sha256"]
                or not isinstance(packet.get("response"), str)
                or sha(packet["response"].encode("utf-8")) != entry["response_sha256"]):
            raise ValueError(f"Blind reviewer packet does not match its source: {review_id}")
        seen_packets.add(review_id)
    if seen_packets != set(mapping):
        raise ValueError("Missing blind reviewer packet")
    reviews_raw = Path(args.reviews).read_bytes()
    document = json.loads(reviews_raw)
    if not isinstance(document, dict) or not isinstance(document.get("reviews"), list):
        raise ValueError("Blind reviews must contain a reviews array")
    translated, seen_reviews = [], set()
    for review in document["reviews"]:
        if not isinstance(review, dict) or {"variant", "case_id"}.intersection(review):
            raise ValueError("Blind reviews use review_id rather than variant/case_id")
        review_id = review.get("review_id")
        if review_id in seen_reviews or review_id not in mapping:
            raise ValueError("Duplicate or unknown blind review ID")
        entry = mapping[review_id]
        if review.get("response_sha256") != entry["response_sha256"]:
            raise ValueError(f"Blind review has a stale response hash: {review_id}")
        translated.append({**{name: value for name, value in review.items() if name != "review_id"},
                           "variant": entry["variant"], "case_id": entry["case_id"]})
        seen_reviews.add(review_id)
    completed = {**{name: value for name, value in document.items() if name != "reviews"}, "reviews": translated,
                 "blind_review_provenance": {"source_review_sha256": sha(reviews_raw),
                                             "review_index_sha256": key["review_index_sha256"],
                                             "private_key_sha256": sha(key_path.read_bytes()),
                                             "scheduled_runs": key["scheduled_runs"],
                                             "reviewed": len(translated), "scheduled": len(mapping)}}
    validate_reviews(completed)
    write_new(destination, json_bytes(completed))
    print(f"Imported {len(translated)}/{len(mapping)} separate blind reviews to {destination}")
