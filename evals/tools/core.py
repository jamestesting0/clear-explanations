"""Portable evaluation primitives. No model or reviewer is invoked here."""
from __future__ import annotations

import hashlib
import json
import math
import re
import stat
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = 1
IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}\Z")
WORD = re.compile(r"[^\W_]+(?:['’\-][^\W_]+)*", re.UNICODE)
CONSTRAINTS = {"max_words", "min_words", "require_table", "forbid_table",
               "exact_sentences", "language", "no_code_change"}
BUNDLE_MODE = "bundled_guide_injection"
BUNDLE_NOTE = ("Bundled-guide injection tests the supplied guidance content, not on-demand "
               "resource selection. Only SKILL.md and direct references/*.md are frozen; "
               "keep evaluation material, README files, prior answers, and answer rubrics outside runtime references.")
RESOURCE_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*\.md\Z")
RESERVED_REFERENCES = {"readme", "rubric", "rubrics", "answer-key", "answer-keys", "answer_key",
                       "answer_keys", "answers", "prior-answers", "prior_answers", "expected-answers",
                       "expected_answers", "responses", "results", "cases", "protocol", "evidence"}


def now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def format_packet(case, skill=None, resources=None):
    """Reconstruct canonical replay bytes; this does not describe surrounding runtime context.

    Keep this format stable: historical packet hashes bind the exact whitespace,
    resource order, headers, and supplied UTF-8 bytes below.
    """
    if skill is not None and resources is not None:
        raise ValueError("Choose a single skill file or runtime resources, not both")
    prompt = ("Answer the single user request below. Return only your answer. "
              "Do not access other evaluation cases, answer keys, reviewer rubrics, or previous responses. "
              "If general style guidance conflicts with the user's explicit request, follow the user's request.\n\n").encode("utf-8")
    if resources is not None:
        prompt += b"## General explanation guidance\n\n"
        prompt += b"The following runtime skill resources are supplied in full.\n\n"
        for resource_path, contents in sorted(resources, key=lambda item: item[0]):
            prompt += (f"### Runtime resource: {resource_path}\n"
                       f"SHA-256: {sha(contents)}; bytes: {len(contents)}\n\n").encode("utf-8")
            prompt += contents + b"\n\n"
    elif skill is not None:
        prompt += b"## General explanation guidance\n\n" + skill + b"\n\n"
    return prompt + ("## User request\n\n" + case["prompt"] + "\n").encode("utf-8")


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def valid_id(value):
    if not isinstance(value, str) or not IDENTIFIER.fullmatch(value):
        raise ValueError(f"Invalid identifier: {value!r}")
    return value


def within(root, relative):
    root = Path(root).resolve()
    result = (root / relative).resolve()
    if result == root or root not in result.parents:
        raise ValueError(f"Path escapes run directory: {relative!r}")
    return result


def runtime_resource_name(relative):
    """Accept a small portable runtime allowlist, never recursive repository content."""
    if relative == "SKILL.md":
        return relative
    if not isinstance(relative, str) or not relative.startswith("references/"):
        raise ValueError(f"Not a runtime resource path: {relative!r}")
    name = relative[len("references/"):]
    if not RESOURCE_NAME.fullmatch(name) or name[:-3].casefold() in RESERVED_REFERENCES:
        raise ValueError(f"Not a runtime reference filename: {relative!r}")
    return relative


def read_runtime_bundle(directory):
    """Read exact UTF-8 bytes from SKILL.md and direct references/*.md only.

    Symlinks (including source-directory ancestors), special files, nonportable
    Markdown filenames, and case-insensitive filename collisions are rejected.
    Other root content and non-Markdown/nested reference content are not read.
    The caller remains responsible for keeping answer keys out of runtime guides.
    """
    root = Path(directory).absolute()
    if any(part.is_symlink() for part in (root, *root.parents)):
        raise ValueError(f"Runtime bundle source must not traverse symlinks: {directory}")
    if not root.is_dir():
        raise ValueError(f"Runtime bundle source is not a directory: {directory}")
    selected = [("SKILL.md", root / "SKILL.md")]
    references = root / "references"
    if references.is_symlink():
        raise ValueError("Runtime references directory must not be a symlink")
    if references.exists():
        if not references.is_dir():
            raise ValueError("Runtime references must be a directory")
        selected.extend((f"references/{path.name}", path)
                        for path in references.iterdir() if path.name.lower().endswith(".md"))
    resources, seen = [], set()
    for relative, path in sorted(selected):
        runtime_resource_name(relative)
        if relative.casefold() in seen:
            raise ValueError(f"Case-insensitive runtime resource collision: {relative}")
        seen.add(relative.casefold())
        if path.is_symlink() or not stat.S_ISREG(path.lstat().st_mode):
            raise ValueError(f"Runtime resource must be a regular file, not a symlink: {relative}")
        raw = path.read_bytes()
        raw.decode("utf-8")
        resources.append((relative, raw))
    return resources


def bundle_digest(resources):
    """Bind names, exact content hashes, and byte lengths independently of run paths."""
    return sha(canonical([{key: resource[key] for key in ("resource_path", "sha256", "bytes")}
                          for resource in sorted(resources, key=lambda item: item["resource_path"])]))


def validate_bundle_packet(packet):
    """Optional schema-1 extension; historical single-file packets need no new fields."""
    fields = {"runtime_resources", "bundle_sha256", "guidance_mode"}
    present = fields.intersection(packet)
    if not present:
        return
    if present != fields or packet["guidance_mode"] != BUNDLE_MODE:
        raise ValueError("Incomplete or unsupported runtime bundle metadata")
    resources = packet["runtime_resources"]
    if not isinstance(resources, list) or not resources:
        raise ValueError("Runtime bundle must name its frozen resources")
    seen, root = set(), None
    for resource in resources:
        if not isinstance(resource, dict) or set(resource) != {"resource_path", "frozen_path", "sha256", "bytes"}:
            raise ValueError("Invalid runtime resource manifest entry")
        name = runtime_resource_name(resource["resource_path"])
        if name.casefold() in seen:
            raise ValueError(f"Duplicate runtime resource: {name}")
        seen.add(name.casefold())
        expected = f"skills/{valid_id(packet['variant'])}/{name}"
        if resource["frozen_path"] != expected:
            raise ValueError(f"Unexpected frozen runtime path: {resource['frozen_path']!r}")
        if not isinstance(resource["sha256"], str) or not re.fullmatch(r"[a-f0-9]{64}", resource["sha256"]):
            raise ValueError(f"Invalid runtime resource hash: {name}")
        if type(resource["bytes"]) is not int or resource["bytes"] < 0:
            raise ValueError(f"Invalid runtime resource byte length: {name}")
        if name == "SKILL.md":
            root = resource
    if root is None or (root["frozen_path"], root["sha256"]) != (packet["frozen_skill_path"], packet["skill_sha256"]):
        raise ValueError("Runtime bundle must bind its SKILL.md to the legacy skill fields")
    if packet["bundle_sha256"] != bundle_digest(resources):
        raise ValueError("Runtime bundle manifest hash mismatch")


def validate_cases(cases):
    if not isinstance(cases, list) or not cases:
        raise ValueError("cases.json must be a nonempty array")
    seen = set()
    required = {"id", "split", "category", "prompt", "constraints"}
    optional = {"source_ids", "complexity_features"}
    for case in cases:
        if not isinstance(case, dict) or not required.issubset(case) or set(case) - required - optional:
            raise ValueError("Each case must contain id, split, category, prompt, constraints; "
                             "only source_ids and complexity_features are optional")
        cid = valid_id(case["id"])
        if cid in seen:
            raise ValueError(f"Duplicate case ID: {cid}")
        seen.add(cid)
        if case["split"] not in {"development", "validation", "holdout"}:
            raise ValueError(f"Invalid split: {cid}")
        if any(not isinstance(case[key], str) or not case[key].strip() for key in ("prompt", "category")):
            raise ValueError(f"Empty or non-string prompt/category: {cid}")
        for field in optional.intersection(case):
            if not isinstance(case[field], list) or any(not isinstance(value, str) or not value.strip() for value in case[field]):
                raise ValueError(f"Invalid {field}; expected an array of nonempty strings: {cid}")
        constraints = case["constraints"]
        if not isinstance(constraints, dict) or set(constraints) - CONSTRAINTS:
            raise ValueError(f"Unknown or invalid constraints: {cid}")
        for key, value in constraints.items():
            if key in {"max_words", "min_words", "exact_sentences"}:
                good = type(value) is int and value >= 0
            elif key in {"require_table", "forbid_table", "no_code_change"}:
                good = type(value) is bool
            else:
                good = isinstance(value, str) and bool(value.strip())
            if not good:
                raise ValueError(f"Invalid {key}: {cid}")
        if constraints.get("min_words", 0) > constraints.get("max_words", float("inf")):
            raise ValueError(f"Conflicting word limits: {cid}")
        if constraints.get("require_table") and constraints.get("forbid_table"):
            raise ValueError(f"Conflicting table requirements: {cid}")
    return cases


def read_index(run):
    index = read_json(Path(run) / "index.json")
    if index.get("schema_version") != SCHEMA or not isinstance(index.get("packets"), list) or not index["packets"]:
        raise ValueError("Unsupported or invalid packet index")
    cases = validate_cases(read_json(Path(run) / "cases.json"))
    by_id = {c["id"]: c for c in cases}
    seen = set()
    for packet in index["packets"]:
        key = (valid_id(packet["variant"]), valid_id(packet["case_id"]))
        if key in seen or key[1] not in by_id:
            raise ValueError(f"Duplicate or unknown packet: {key}")
        seen.add(key)
        within(run, packet["prompt_path"])
        if packet["frozen_skill_path"]:
            within(run, packet["frozen_skill_path"])
        validate_bundle_packet(packet)
        for resource in packet.get("runtime_resources", []):
            within(run, resource["frozen_path"])
    return index, by_id


def select_packets(index, variant=None, ids=None):
    requested = set(ids.split(",")) if ids else None
    packets = [p for p in index["packets"] if (not variant or p["variant"] == variant)
               and (not requested or p["case_id"] in requested)]
    if not packets or (requested and requested - {p["case_id"] for p in packets}):
        raise ValueError("Selection is empty or includes unknown case IDs")
    return packets


def paths(run, packet):
    base = Path(run) / "outputs" / valid_id(packet["variant"]) / valid_id(packet["case_id"])
    return base.with_suffix(".md"), base.with_suffix(".meta.json")


def packet_integrity(run, packet, case):
    errors = []
    for field, hash_field in (("prompt_path", "prompt_sha256"), ("frozen_skill_path", "skill_sha256")):
        if packet[field] is None:
            if packet[hash_field] is not None:
                errors.append(f"{field}: inconsistent null hash")
            continue
        try:
            path = within(run, packet[field])
            matches = path.is_file() and sha(path.read_bytes()) == packet[hash_field]
        except (OSError, ValueError):
            matches = False
        if not matches:
            errors.append(f"{field}: missing or hash mismatch")
    try:
        validate_bundle_packet(packet)
        if "runtime_resources" in packet:
            actual = dict(read_runtime_bundle(Path(run) / "skills" / packet["variant"]))
            expected = {resource["resource_path"] for resource in packet["runtime_resources"]}
            if set(actual) != expected:
                errors.append("runtime resource inventory mismatch")
            for resource in packet["runtime_resources"]:
                raw = actual.get(resource["resource_path"])
                if raw is None or sha(raw) != resource["sha256"] or len(raw) != resource["bytes"]:
                    errors.append(f"runtime resource {resource['resource_path']}: missing or hash/byte mismatch")
    except (OSError, ValueError, KeyError, TypeError) as error:
        errors.append(f"runtime bundle integrity failure: {error}")
    if sha(canonical(case)) != packet["case_sha256"]:
        errors.append("case snapshot hash mismatch")
    return errors


def collect(run, packet, case, response, metadata, stderr=None):
    """Write response bytes unchanged; never replace an earlier response."""
    integrity = packet_integrity(run, packet, case)
    if integrity:
        raise ValueError("Cannot collect against altered packet: " + "; ".join(integrity))
    if not isinstance(response, bytes) or not isinstance(metadata, dict):
        raise ValueError("Collection requires raw bytes and an object of metadata")
    output, meta_path = paths(run, packet)
    output.parent.mkdir(parents=True, exist_ok=True)
    meta = {
        "schema_version": SCHEMA, "case_id": packet["case_id"], "variant": packet["variant"],
        "skill_sha256": packet["skill_sha256"], "prompt_sha256": packet["prompt_sha256"],
        "prompt_sha256_role": metadata.get("prompt_sha256_role", "canonical_replay_packet"),
        "runtime_prompt_sha256": metadata.get("runtime_prompt_sha256"),
        "case_sha256": packet["case_sha256"], "response_sha256": sha(response),
        "response_path": str(output.relative_to(Path(run))), "response_bytes": len(response),
        "started_at": metadata.get("started_at"), "completed_at": metadata.get("completed_at"),
        "collected_at": now(), "transport": metadata.get("transport", "manual-import"),
        "model_requested": metadata.get("model_requested"), "model_observed": metadata.get("model_observed"),
        "status": metadata.get("status", "completed"), "source_metadata": metadata,
    }
    if "bundle_sha256" in packet:
        meta.update(bundle_sha256=packet["bundle_sha256"], guidance_mode=packet["guidance_mode"])
    with output.open("xb") as handle:
        handle.write(response)
    if stderr is not None:
        diagnostic = output.with_suffix(".stderr")
        with diagnostic.open("xb") as handle:
            handle.write(stderr)
        meta.update(stderr_path=str(diagnostic.relative_to(Path(run))), stderr_sha256=sha(stderr))
    with meta_path.open("x", encoding="utf-8") as handle:
        json.dump(meta, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    with (Path(run) / "manifest.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(meta, ensure_ascii=False) + "\n")
    return meta


def word_count(text):
    return len(WORD.findall(text))


def unfenced_lines(text):
    fence = None
    for line in text.splitlines():
        opening = re.match(r"^\s{0,3}(`{3,}|~{3,})", line)
        if opening:
            marker = opening.group(1)
            if fence is None:
                fence = marker
            elif marker[0] == fence[0] and len(marker) >= len(fence):
                fence = None
            continue
        if fence is None:
            yield line


def markdown_table(text):
    previous = ""
    for line in unfenced_lines(text):
        cells = line.strip().strip("|").split("|")
        if len(cells) >= 2 and "|" in previous and all(re.fullmatch(r"\s*:?-{3,}:?\s*", c) for c in cells):
            return True
        previous = line
    return False


def constraint_checks(text, constraints):
    count = word_count(text)
    table = markdown_table(text)
    checks = []
    for key, expected in constraints.items():
        result = {"constraint": key, "expected": expected, "kind": "deterministic"}
        if key in {"min_words", "max_words"}:
            result.update(observed=count, passed=count >= expected if key == "min_words" else count <= expected)
        elif key in {"require_table", "forbid_table"}:
            result.update(observed=table, passed=(table if key == "require_table" else not table) if expected else True)
        elif key == "exact_sentences":
            estimate = len(re.findall(r"[^.!?]+[.!?]+(?:[\"'’”)]*)?(?=\s|$)|[^.!?]+$", text.strip()))
            result.update(kind="heuristic", observed=estimate, matches_estimate=estimate == expected,
                          passed=None, note="Sentence boundaries are ambiguous; semantic review must confirm.")
        else:
            result.update(kind="semantic", passed=None, note="Requires separate review; no regex quality claim.")
        checks.append(result)
    return checks


def validate_reviews(document):
    """Validate reviewer judgments without converting them into mechanical scores."""
    if not isinstance(document, dict) or document.get("schema_version") != SCHEMA or not isinstance(document.get("reviews"), list):
        raise ValueError("Review document must have schema_version:1 and a reviews array")
    if not isinstance(document.get("reviewer"), str) or not document["reviewer"].strip():
        raise ValueError("Review document must name its reviewer")
    reviews = {}
    for entry in document["reviews"]:
        key = (valid_id(entry["variant"]), valid_id(entry["case_id"]))
        if key in reviews or entry.get("verdict") not in {"pass", "partial", "fail"}:
            raise ValueError(f"Duplicate review or invalid verdict: {key}")
        if not re.fullmatch(r"[a-f0-9]{64}", entry.get("response_sha256", "")):
            raise ValueError(f"Review must bind to response_sha256: {key}")
        if not isinstance(entry.get("rationale"), str):
            raise ValueError(f"Review must provide a rationale: {key}")
        if "score" in entry or "max_score" in entry:
            score, maximum = entry.get("score"), entry.get("max_score")
            if type(score) not in {int, float} or type(maximum) not in {int, float} or not math.isfinite(score) or not math.isfinite(maximum) or not 0 <= score <= maximum or not maximum > 0:
                raise ValueError(f"Invalid review score range: {key}")
        criteria = entry.get("criteria", [])
        if not isinstance(criteria, list) or any(not isinstance(c, dict) or c.get("verdict") not in {"pass", "partial", "fail"} or not isinstance(c.get("criterion"), str) or not isinstance(c.get("notes", ""), str) for c in criteria):
            raise ValueError(f"Invalid review criteria: {key}")
        reviews[key] = entry
    return reviews


def load_reviews(path):
    if path is None:
        return {}, {}
    document = read_json(path)
    reviews = validate_reviews(document)
    header = {k: v for k, v in document.items() if k != "reviews"}
    header["review_file_sha256"] = sha(Path(path).read_bytes())
    return reviews, header


def evaluate(run, reviews_path=None, allow_extra_reviews=False):
    index, cases = read_index(run)
    reviews, review_header = load_reviews(reviews_path)
    known = {(p["variant"], p["case_id"]) for p in index["packets"]}
    if not allow_extra_reviews and set(reviews) - known:
        raise ValueError("Review document contains an unknown variant or case")
    manifest, manifest_errors = {}, []
    try:
        for line in (Path(run) / "manifest.jsonl").read_text(encoding="utf-8").splitlines():
            entry = json.loads(line)
            key = (entry["variant"], entry["case_id"])
            if key in manifest or key not in known:
                raise ValueError("duplicate or unknown manifest entry")
            manifest[key] = entry
    except (OSError, ValueError, KeyError, TypeError):
        manifest_errors.append("missing or invalid collection manifest")
    results = []
    for packet in index["packets"]:
        case = cases[packet["case_id"]]
        output, meta_path = paths(run, packet)
        errors = packet_integrity(run, packet, case) + manifest_errors
        raw, meta = b"", None
        if output.is_file():
            raw = output.read_bytes()
        else:
            errors.append("missing response")
        if not raw.strip():
            errors.append("empty response")
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            text = raw.decode("utf-8", errors="replace")
            errors.append("response is not valid UTF-8")
        if meta_path.is_file():
            try:
                meta = read_json(meta_path)
                for field in ("variant", "case_id", "skill_sha256", "prompt_sha256", "case_sha256"):
                    if meta.get(field) != packet[field]:
                        errors.append(f"metadata {field} mismatch")
                for field in ("bundle_sha256", "guidance_mode"):
                    if meta.get(field) != packet.get(field):
                        errors.append(f"metadata {field} mismatch")
                if meta.get("response_sha256") != sha(raw):
                    errors.append("response hash mismatch")
                if meta.get("status") != "completed":
                    errors.append("response collection did not complete successfully")
                if manifest.get((packet["variant"], packet["case_id"])) != meta:
                    errors.append("manifest and response metadata mismatch")
            except (ValueError, TypeError, AttributeError):
                errors.append("invalid response metadata")
        else:
            errors.append("missing response metadata")
        checks = constraint_checks(text, case["constraints"])
        review = reviews.get((packet["variant"], packet["case_id"]))
        review_state = "unreviewed"
        if review:
            review_state = "valid" if review["response_sha256"] == sha(raw) and not errors else "invalid"
        deterministic_ok = not errors and all(c["passed"] is not False for c in checks)
        results.append({"case_id": packet["case_id"], "variant": packet["variant"], "case": case,
                        "response": text, "response_sha256": sha(raw) if output.is_file() else None,
                        "metadata": meta, "errors": errors, "word_count": word_count(text), "checks": checks,
                        "deterministic_pass": deterministic_ok, "review_state": review_state, "review": review,
                        "fully_reviewed_pass": deterministic_ok and review_state == "valid" and review["verdict"] == "pass"})
    return {"schema_version": SCHEMA, "generated_at": now(), "run_name": index.get("name"),
            "review_provenance": review_header, "results": results}


def evaluate_many(runs, reviews_path=None):
    """Combine only explicitly scheduled packets, rejecting ambiguous duplicates."""
    variant_fingerprints = {}
    for run in runs:
        index, _ = read_index(run)
        for packet in index["packets"]:
            fingerprint = (packet["skill_sha256"], packet.get("bundle_sha256"), packet.get("guidance_mode"))
            if variant_fingerprints.setdefault(packet["variant"], fingerprint) != fingerprint:
                raise ValueError(f"Different guidance shares one variant across runs: {packet['variant']}")
    reports = [evaluate(run, reviews_path, allow_extra_reviews=True) for run in runs]
    records = [record for report in reports for record in report["results"]]
    known, case_hashes = set(), {}
    for record in records:
        key = (record["variant"], record["case_id"])
        if key in known:
            raise ValueError(f"Duplicate scheduled variant/case across runs: {key}")
        known.add(key)
        fingerprint = sha(canonical(record["case"]))
        if case_hashes.setdefault(record["case_id"], fingerprint) != fingerprint:
            raise ValueError(f"Different cases share one ID across runs: {record['case_id']}")
    reviews, header = load_reviews(reviews_path)
    if set(reviews) - known:
        raise ValueError("Review document contains an unscheduled variant or case")
    sources = [{"name": report["run_name"], "index_sha256": sha((Path(run) / "index.json").read_bytes())}
               for run, report in zip(runs, reports)]
    header["scheduled_runs"] = sources
    return {"schema_version": SCHEMA, "generated_at": now(),
            "run_name": " + ".join(str(report["run_name"]) for report in reports),
            "review_provenance": header, "results": records}
